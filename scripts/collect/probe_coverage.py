"""Discover which storefronts and languages actually carry reviews.

Both stores expose reviews for the same app but partition them along different
axes, and getting that wrong is the most expensive mistake in this pipeline:

    App Store   partitions by COUNTRY. Each storefront holds its own reviews.
    Google Play partitions by LANGUAGE. en/us, en/gb, en/ca, en/au and en/in
                return identical sets, so country is pinned and only the
                language varies.

Output feeds the scrapers automatically. Without it they fall back to a
shortlist of 13 countries and 10 languages.

    coverage_appstore.json  {country: reviews_on_page_1}
                             0 -> storefront exists, no reviews for this app
                            -1 -> no storefront (Apple answers HTTP 400)
    coverage_gplay.json     {language: {"got": int, "new": int}}
                            new == 0, got > 0  -> duplicate of an earlier
                                                  language, skip it
                            new == 0, got == 0 -> no reviews in that language

Measured 2026-09-19: 249 country codes -> 100-124 live storefronts;
72 language codes -> 47 languages with their own layer. The country figure is
a range because the RSS feed intermittently returns an empty page for a
populated storefront (see RETRY_EMPTY).

Usage:
    python scripts/collect/probe_coverage.py [appstore|gplay|both]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import APP_STORE_ID, COLLECT, GOOGLE_PLAY_PACKAGE, http_get, write_json

log = logging.getLogger(__name__)

# Eight concurrent requests is where Apple stops throttling a 249-code sweep.
MAX_WORKERS = 8

# An empty page does not prove a storefront is empty. Two sweeps of the same
# codes returned 100 and 124 live storefronts with an identical set of hard
# failures, so empties are retried once and hard failures are not — HTTP 400
# reproduces deterministically for codes with no storefront.
RETRY_EMPTY = 1
RETRY_BACKOFF_SECONDS = 0.5

# Written when a request could not be completed or parsed, as opposed to
# completing with zero reviews.
PROBE_FAILED = -1

# Sample size per language: enough to answer "does this language have its own
# reviews", never used to measure volume.
GPLAY_PROBE_SAMPLE = 150

# Sweeping the whole ISO 3166-1 space rather than a curated list is deliberate:
# Apple publishes no list of storefronts carrying a given app, and guessing
# under-counts the long tail.
COUNTRY_CODES = """
ad ae af ag ai al am ao aq ar as at au aw ax az ba bb bd be bf bg bh bi bj
bl bm bn bo bq br bs bt bv bw by bz ca cc cd cf cg ch ci ck cl cm cn co cr cu cv cw cx cy cz
de dj dk dm do dz ec ee eg eh er es et fi fj fk fm fo fr ga gb gd ge gf gg gh gi gl gm gn gp
gq gr gs gt gu gw gy hk hm hn hr ht hu id ie il im in io iq ir is it je jm jo jp ke kg kh ki
km kn kp kr kw ky kz la lb lc li lk lr ls lt lu lv ly ma mc md me mf mg mh mk ml mm mn mo mp
mq mr ms mt mu mv mw mx my mz na nc ne nf ng ni nl no np nr nu nz om pa pe pf pg ph pk pl pm
pn pr ps pt pw py qa re ro rs ru rw sa sb sc sd se sg sh si sj sk sl sm sn so sr ss st sv sx
sy sz tc td tf tg th tj tk tl tm tn to tr tt tv tw tz ua ug um us uy uz va vc ve vg vi vn vu
wf ws ye yt za zm zw
""".split()

# Narrower than full ISO 639-1: Google rejects codes it does not serve, and a
# rejection is indistinguishable from "no reviews" in the response.
LANGUAGE_CODES = """
af am ar az be bg bn bs ca cs da de el en es et eu fa fi fil fr gl gu he hi hr hu
hy id is it ja ka kk km kn ko ky lo lt lv mk ml mn mr ms my ne nl no pa pl pt ro ru si sk sl
sq sr sv sw ta te th tr uk ur uz vi zh zu
""".split()


def probe_country(country: str) -> tuple[str, int]:
    """Count reviews on page 1 of a storefront, or PROBE_FAILED."""
    url = (f"https://itunes.apple.com/{country}/rss/customerreviews/page=1"
           f"/id={APP_STORE_ID}/sortby=mostrecent/json")

    for attempt in range(RETRY_EMPTY + 1):
        try:
            payload = json.loads(http_get(url))
        except Exception as exc:
            log.debug("%s: %s", country, exc)
            return country, PROBE_FAILED

        entries = payload.get("feed", {}).get("entry", [])
        if isinstance(entries, dict):      # a one-review feed is a bare object
            entries = [entries]
        count = sum(1 for entry in entries if "im:rating" in entry)

        if count or attempt == RETRY_EMPTY:
            return country, count
        time.sleep(RETRY_BACKOFF_SECONDS)

    return country, 0


def probe_app_store() -> dict[str, int]:
    results: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(probe_country, code) for code in COUNTRY_CODES]
        for done, future in enumerate(as_completed(futures), start=1):
            country, count = future.result()
            results[country] = count
            if done % 40 == 0:
                log.info("swept %d/%d codes", done, len(COUNTRY_CODES))

    live = sorted(c for c, n in results.items() if n > 0)
    log.info("App Store: %d codes swept", len(COUNTRY_CODES))
    log.info("  %3d storefronts with reviews", len(live))
    log.info("  %3d with none", sum(1 for n in results.values() if n == 0))
    log.info("  %3d with no storefront", sum(1 for n in results.values() if n < 0))
    log.info("  live: %s", " ".join(live))

    write_json(results, f"{COLLECT}/coverage_appstore.json")
    log.info("wrote coverage_appstore.json")
    return results


def probe_google_play() -> dict[str, dict]:
    """Sweep languages, keeping those with review IDs not seen earlier.

    Languages share one `seen` set, so `new` measures novelty against every
    language probed before it. Order-dependent by design: of two languages
    returning the same set, the first claims it and the second is marked as a
    duplicate to skip.
    """
    from google_play_scraper import Sort, reviews   # optional dependency

    seen: set[str] = set()
    results: dict[str, dict] = {}

    for language in LANGUAGE_CODES:
        try:
            batch, _ = reviews(GOOGLE_PLAY_PACKAGE, lang=language, country="us",
                               sort=Sort.NEWEST, count=GPLAY_PROBE_SAMPLE)
        except Exception as exc:
            log.debug("%s: %s", language, exc)
            results[language] = {"got": PROBE_FAILED, "new": PROBE_FAILED}
            continue

        novel = sum(1 for review in batch if review["reviewId"] not in seen)
        seen.update(review["reviewId"] for review in batch)
        results[language] = {"got": len(batch), "new": novel}
        if novel:
            log.info("  %-4s got %4d, new %4d", language, len(batch), novel)

    distinct = sorted(k for k, v in results.items() if v["new"] > 0)
    log.info("Google Play: %d codes swept", len(LANGUAGE_CODES))
    log.info("  %3d languages with their own layer", len(distinct))
    log.info("  languages: %s", " ".join(distinct))

    write_json(results, f"{COLLECT}/coverage_gplay.json")
    log.info("wrote coverage_gplay.json")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("target", nargs="?", default="both",
                        choices=("appstore", "gplay", "both"),
                        help="which store to probe (default: both)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="report per-code failures")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(message)s")

    started = time.time()
    if args.target in ("appstore", "both"):
        probe_app_store()
    if args.target in ("gplay", "both"):
        probe_google_play()
    log.info("done in %.0fs", time.time() - started)
    return 0


if __name__ == "__main__":
    sys.exit(main())
