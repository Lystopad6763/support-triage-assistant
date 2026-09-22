"""Scrape Google Play reviews, one file per language.

Partitioned by LANGUAGE, not country: en/us, en/gb, en/ca, en/au and en/in
return identical sets, so country is pinned and only the language varies.
Language list comes from probe_coverage.py.

Unlike App Store, a near-complete pull is possible here — roughly 425
reviews/s via continuation_token pagination.

One file per language, mirroring App Store's one file per page. An earlier
version accumulated everything and wrote once at the end, so a crash on the
40th of 47 languages lost the whole run. Now each language lands immediately
and a re-run skips languages that already have a file.

Cross-language dedup is deliberately absent: normalize.py dedupes by uid
anyway, and a shared `seen` set was the only reason to hold everything in
memory.

filter_score_with is never used, so the rating distribution is natural and
safe for statistics.

Output: raw/googleplay/{lang}.json

Usage:
    python scripts/collect/scrape_all_gplay.py [cap] [--since] [--force]
"""
from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone

from google_play_scraper import Sort, reviews

from common import (GOOGLE_PLAY_PACKAGE, RAW_GOOGLEPLAY, audit_pii,
                    load_coverage, redact_reply, redact_review, report_audit,
                    self_test, write_json)

FALLBACK_LANGS = ["en", "es", "pt", "fr", "de", "it", "nl", "pl", "ru", "uk"]
LANGS = load_coverage("coverage_gplay.json",
                      lambda v: v.get("new", 0) > 0, FALLBACK_LANGS)

PINNED_COUNTRY = "us"
PAGE_SIZE = 200

def pull(lang: str, cap: int, since: str | None) -> list:
    """Paginate one language until the cap, the end of the feed, or `since`.

    Reviews are newest-first, so once a batch's oldest entry predates the
    cutoff every later batch does too. Entries past the cutoff are dropped from
    the straddling batch, which makes the cutoff exact rather than approximate.
    """
    token, collected = None, []
    while len(collected) < cap:
        try:
            batch, token = reviews(GOOGLE_PLAY_PACKAGE, lang=lang,
                                   country=PINNED_COUNTRY, sort=Sort.NEWEST,
                                   count=PAGE_SIZE, continuation_token=token)
        except Exception as exc:
            print(f"   !! {lang}: {exc}")
            break
        if not batch:
            break

        if since:
            in_range = [r for r in batch if str(r["at"])[:10] >= since]
            collected += in_range
            if len(in_range) < len(batch):
                break        # batch straddled the cutoff; the rest is older
        else:
            collected += batch

        if token is None:
            break
    return collected


def to_record(lang: str, raw: list) -> dict:
    """Flatten one page of reviews, redacting both sides.

    The review body gets redacted too, not just the reply: reviewers volunteer
    their own name, their social handles and their birth date and time.
    userName and userImage are dropped by never being read.
    """
    rows = [{
        "reviewId": r["reviewId"],
        "score": r["score"],
        "content": redact_review(r["content"] or ""),
        "reply": redact_reply(r.get("replyContent") or ""),
        "at": str(r["at"]),
        "repliedAt": str(r.get("repliedAt")),
        "version": r.get("reviewCreatedVersion"),
        "thumbsUp": r["thumbsUpCount"],
    } for r in raw]

    return {
        # Provenance in the file, not only in its name, which is easy to lose.
        "store": "googleplay",
        "lang": lang,
        "country": PINNED_COUNTRY,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(rows),
        # Always null here: this scraper never uses filter_score_with. The
        # field exists so a differently-sampled dump can declare itself.
        "sampled_with_filter": None,
        "reviews": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("cap", nargs="?", type=int, default=20000,
                        help="maximum reviews per language (default: 20000)")
    parser.add_argument("--since", metavar="YYYY-MM-DD",
                        help="keep only reviews on or after this date. Google "
                             "Play has no date filter but is newest-first, so "
                             "pagination stops at the cutoff — this cuts "
                             "runtime as well as volume, and is exact.")
    parser.add_argument("--force", action="store_true",
                        help="re-fetch languages that already have a file "
                             "(default: skip, making a re-run after a crash cheap)")
    args = parser.parse_args()

    # Refuse to collect anything if redaction or its audit has regressed.
    broken = self_test()
    if broken:
        print("!! REDACTION SELF-TEST FAILED, nothing was collected")
        for problem in broken:
            print(f"   {problem}")
        raise SystemExit(1)

    os.makedirs(RAW_GOOGLEPLAY, exist_ok=True)
    started = time.time()
    total = skipped = 0
    leftovers: list[tuple[str, str]] = []
    audited = 0

    for lang in LANGS:
        path = os.path.join(RAW_GOOGLEPLAY, f"{lang}.json")
        if os.path.exists(path) and not args.force:
            skipped += 1
            continue

        lang_started = time.time()
        record = to_record(lang, pull(lang, args.cap, args.since))

        # Verify before writing: a redaction regression must fail here, not
        # after the data is published. Both fields — the review body is where
        # people name themselves.
        fields = [r[field] for r in record["reviews"]
                  for field in ("content", "reply")]
        leftovers += audit_pii(fields)
        audited += len(fields)
        write_json(record, path)

        total += record["count"]
        print(f"  {lang:<4} {record['count']:6d} reviews  "
              f"({time.time() - lang_started:.0f}s)")

    print("")
    report_audit(leftovers, audited)

    print(f"{total} reviews, {len(LANGS) - skipped} languages processed, "
          f"{skipped} skipped, {time.time() - started:.0f}s -> {RAW_GOOGLEPLAY}")
    if skipped:
        print("  (skipped languages already have a file; --force to refetch)")


if __name__ == "__main__":
    main()
