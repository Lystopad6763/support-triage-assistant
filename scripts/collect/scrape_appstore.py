"""Scrape App Store reviews, one file per country storefront.

Endpoint — the same-origin proxy Apple's own web page uses:
    https://apps.apple.com/api/apps/v1/catalog/{country}/apps/{id}/reviews

Found in the store page's JS bundle as
    useRelativeProxyFor: {"https://amp-api.apps.apple.com/": "/api/apps/"}
The upstream amp-api answers 401 without a bearer token that Apple no longer
exposes anywhere reachable; the proxy needs no token at all.

This replaces the older RSS feed (itunes.apple.com/.../customerreviews), which
was worse in every respect:

                        RSS              proxy
    developer replies   none             ~97% of reviews
    depth               ~500/country     1200+ and still paginating
    pagination holes    yes, structural  none observed
    fields              no isEdited      isEdited present

The RSS feed predates developer responses (2017) and was never updated, which
is why it carries none.

RATE LIMIT
    Measured to be per IP, not per account or key: the proxy returns 429 while
    the plain store page on the same host still serves 813KB, and switching VPN
    exit resets it immediately. So the workflow is: run, let it stop when the
    quota closes, switch exit, run again. Countries already on disk are skipped,
    which makes that loop cheap.

    A limited country is never written. An empty file would look finished on the
    next run and drop the country from the dataset for good — that bug cost 16
    countries once already, silently.

    The storefront is named in the URL path, so the VPN exit does not change
    which reviews come back. It only decides whether Apple answers.

Caveats:
  - undocumented internal proxy, so it can change without notice
  - userName is returned and dropped here, never reaching disk
  - both sides are redacted before writing: developer replies greet customers
    by name, and review bodies carry the reviewer's own name and birth data
    (see the Redaction section of common.py)

Partitioned by COUNTRY: each storefront holds its own reviews. Country list
comes from probe_coverage.py.

Output: raw/appstore/{country}.json

Usage:
    python data/collect/scripts/scrape_appstore.py [cap] [--since] [--force]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time
import urllib.error
from datetime import datetime, timezone

from common import (APP_STORE_ID, RAW_APPSTORE, audit_pii, http_get,
                    load_coverage, redact_reply, redact_review, report_audit,
                    self_test, write_json)

FALLBACK_COUNTRIES = ["us", "gb", "ca", "au", "ua", "de", "fr", "es",
                      "it", "nl", "pl", "br", "mx"]
COUNTRIES = load_coverage("coverage_appstore.json", lambda n: n > 0,
                          FALLBACK_COUNTRIES)

# The /apps/ segment is not decoration: it is the half of the proxy mapping
# that stands in for amp-api.apps.apple.com. Without it every request is a 404.
PROXY = "https://apps.apple.com/api/apps"
HEADERS = {"Origin": "https://apps.apple.com",
           "Referer": "https://apps.apple.com/"}

PAGE_SIZE = 20                   # the proxy caps a page at 20 regardless
PACE_SECONDS = 0.35              # opening pace, raised for the rest of the run
PACE_CEILING = 2.5
PACE_GROWTH = 1.8
RETRY_ON_429 = 4
BACKOFF_SECONDS = 10             # doubles per attempt: 10, 20, 40, 80

# The pace is global and one-way: once Apple starts pushing back it does not
# stop for the rest of the sweep, so resetting per country just walks back into
# the wall.
_pace = {"seconds": PACE_SECONDS}


class RateLimited(Exception):
    """Apple refused for long enough that the sweep has to stop."""


def preflight() -> bool:
    """One cheap request to see whether Apple is talking to us at all.

    Answers in 0.2s what the sweep would otherwise take minutes of backoff to
    discover, which matters when the fix is to switch VPN exit and retry.

    Returns False when the quota is closed. Any other HTTP status means the
    undocumented proxy itself moved, which is a different problem and says so
    rather than arriving as a traceback.
    """
    try:
        http_get(f"{PROXY}/v1/catalog/us/apps/{APP_STORE_ID}/reviews"
                 f"?l=en-US&offset=0&limit=1&platform=web", headers=HEADERS)
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            return False
        raise SystemExit(
            f"The proxy answered HTTP {exc.code} for a request that should "
            f"work:\n  {PROXY}/v1/catalog/us/apps/{APP_STORE_ID}/reviews\n"
            f"  Apple can change this endpoint without notice — check the "
            f"useRelativeProxyFor mapping in the store page's JS bundle.")


def fetch_page(path: str) -> dict:
    """Fetch one page, retrying on HTTP 429 with a doubling backoff."""
    for attempt in range(RETRY_ON_429 + 1):
        try:
            return json.loads(http_get(PROXY + path, headers=HEADERS))
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            _pace["seconds"] = min(PACE_CEILING, _pace["seconds"] * PACE_GROWTH)
            if attempt == RETRY_ON_429:
                raise RateLimited(f"still 429 after {RETRY_ON_429} retries")
            time.sleep(BACKOFF_SECONDS * (2 ** attempt))
    return {}


def pull(country: str, cap: int, since: str | None) -> tuple[list[dict], bool]:
    """Paginate one storefront until the cap, the end, or `since`.

    Returns (reviews, complete). `complete` is False when the sweep was cut
    short, and the caller then writes nothing — see RATE LIMIT above.

    Reviews arrive newest-first, so once a page's oldest entry predates the
    cutoff every later page does too. Entries past the cutoff are dropped from
    the straddling page, which makes the cutoff exact rather than approximate.
    """
    path = (f"/v1/catalog/{country}/apps/{APP_STORE_ID}/reviews"
            f"?l=en-US&offset=0&limit={PAGE_SIZE}&platform=web")
    collected: list[dict] = []

    while path and len(collected) < cap:
        try:
            payload = fetch_page(path)
        except RateLimited:
            raise
        except Exception as exc:
            print(f"   !! {country}: {exc}")
            return collected, False

        rows = payload.get("data", [])
        if not rows:
            break

        reviews = [shape(row) for row in rows]
        if since:
            in_range = [r for r in reviews if r["date"][:10] >= since]
            collected += in_range
            if len(in_range) < len(reviews):
                break        # page straddled the cutoff; the rest is older
        else:
            collected += reviews

        path = payload.get("next")
        if path and "limit" not in path:
            path += f"&limit={PAGE_SIZE}&platform=web"
        time.sleep(_pace["seconds"])

    return collected, True


def shape(row: dict) -> dict:
    """Flatten one API row, dropping identity and redacting both sides.

    userName is discarded rather than stored: the pipeline never reads it, it
    carries no classification signal, and many reviewers are EU residents.

    The review body gets redacted too, not just the reply. Reviewers volunteer
    their own name, their social handles and — this being a horoscope app —
    their birth date and time.
    """
    attributes = row.get("attributes", {})
    response = attributes.get("developerResponse") or {}
    return {
        "id": row.get("id"),
        "rating": attributes.get("rating"),
        "title": redact_review(attributes.get("title", "")),
        "text": redact_review(attributes.get("review", "")),
        "date": attributes.get("date"),
        "is_edited": attributes.get("isEdited", False),
        "reply": redact_reply(response.get("body") or ""),
        "reply_date": response.get("modified"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("cap", nargs="?", type=int, default=2000,
                        help="maximum reviews per country (default: 2000)")
    parser.add_argument("--since", metavar="YYYY-MM-DD",
                        help="keep only reviews on or after this date. The API "
                             "has no date filter but is newest-first, so "
                             "pagination stops at the cutoff — this cuts "
                             "runtime as well as volume, and is exact.")
    parser.add_argument("--force", action="store_true",
                        help="re-fetch countries that already have a file "
                             "(default: skip, so a re-run continues a sweep)")
    parser.add_argument("--pace", type=float, default=PACE_SECONDS,
                        metavar="SECONDS",
                        help=f"seconds between pages (default: {PACE_SECONDS}). "
                             f"Raising it to 1-2 gets further into the quota "
                             f"before it closes.")
    args = parser.parse_args()
    _pace["seconds"] = args.pace

    # Refuse to collect anything if redaction or its audit has regressed.
    broken = self_test()
    if broken:
        print("!! REDACTION SELF-TEST FAILED, nothing was collected")
        for problem in broken:
            print(f"   {problem}")
        raise SystemExit(1)

    if not preflight():
        print("Apple is rate limiting this IP — nothing was attempted.\n"
              "  Switch VPN exit and re-run; countries already on disk are "
              "skipped, so nothing is lost or repeated.")
        raise SystemExit(0)

    os.makedirs(RAW_APPSTORE, exist_ok=True)
    started = time.time()
    total = with_reply = skipped = audited = 0
    leftovers: list[tuple[str, str]] = []

    for country in COUNTRIES:
        path = os.path.join(RAW_APPSTORE, f"{country}.json")
        if os.path.exists(path) and not args.force:
            skipped += 1
            continue

        country_started = time.time()
        try:
            reviews, complete = pull(country, args.cap, args.since)
        except RateLimited as exc:
            # The quota is per IP, so the next country would fail the same way.
            print(f"  {country:<4} RATE LIMITED ({exc}), nothing written")
            break

        if not complete:
            print(f"  {country:<4} INCOMPLETE, nothing written")
            continue

        # Verify before writing: a redaction regression must fail here, not
        # after the data is published. Every text-bearing field, not just the
        # reply — the review body is where people name themselves.
        fields = [r[field] for r in reviews
                  for field in ("title", "text", "reply")]
        leftovers += audit_pii(fields)
        audited += len(fields)

        replies = sum(1 for r in reviews if r["reply"])
        write_json({
            # Provenance in the file, not only in its name, which is easy to lose.
            "store": "appstore",
            "country": country,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "count": len(reviews),
            "with_reply": replies,
            "reviews": reviews,
        }, path)

        total += len(reviews)
        with_reply += replies
        print(f"  {country:<4} {len(reviews):5d} reviews, {replies:5d} with reply  "
              f"({time.time() - country_started:.0f}s)")

    print("")
    report_audit(leftovers, audited)

    on_disk = {os.path.basename(p)[:-len(".json")]
               for p in glob.glob(os.path.join(RAW_APPSTORE, "*.json"))}
    missing = [c for c in COUNTRIES if c not in on_disk]
    print(f"{total} reviews ({with_reply} with a developer reply) in "
          f"{time.time() - started:.0f}s -> {RAW_APPSTORE}")
    print(f"  {len(on_disk)} of {len(COUNTRIES)} countries on disk, "
          f"{skipped} skipped as already collected")
    if missing:
        print(f"  {len(missing)} still missing: {' '.join(missing)}")
        print("  switch VPN exit and re-run to continue")


if __name__ == "__main__":
    main()
