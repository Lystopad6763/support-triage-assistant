"""Merge App Store and Google Play dumps into one corpus.

Both scrapers already unwrap their store's quirks, so this is mostly field
renaming plus four derived fields. Output: data/corpus.jsonl, one JSON object
per line.

READ ORDER MATTERS
    Google Play files are sorted so dumps WITHOUT score sampling
    (sampled_with_filter = null) are read first. Dedup keeps the first record
    seen, so a review present in both a natural and an oversampled pull keeps
    its natural provenance — otherwise the rating distribution would lie.

SCHEMA
    field                type       AppStore  GooglePlay  meaning
    uid                  str        100%      100%   dedup key, as:/gp: prefix
    store                str        100%      100%   appstore | googleplay
    locale               str        100%      100%   QUERY PARAMETER, not user data
    score                int        100%      100%   1-5
    title                str        100%        0%   Google Play has no titles
    text                 str        100%      100%   review body
    date                 str        100%      100%   YYYY-MM-DD
    app_version          str          0%       74%   Google Play only
    thumbs_up            int          0%      100%   Google Play only
    official_reply       str         97%       99%   support reply
    reply_date           str         97%       99%
    reply_latency_sec    int         97%       99%   reply time - review time
    sampled_with_filter  int|null   null   null|1|2  score-sampled or natural
    chars                int         derived        len(text)
    is_complaint         bool        derived        score <= 2
    usable_as_ticket     bool        derived        chars >= 150
    reply_channel        str          0%       68%   address quoted in the reply
    reply_channel_valid  bool         0%       68%   is it an allowed address

TWO RULES
    1. Only App Store records carry a title; only Google Play records carry
       app_version and thumbs_up. Nothing is universal except the review text
       itself, so never assume a field is populated without checking `store`.
       (This used to read "title and official_reply are mutually exclusive" —
       true of the RSS feed, false since the App Store scraper moved to Apple's
       proxy API, which returns developer replies.)
    2. locale IS NOT THE LANGUAGE OF THE TEXT. ru/ua held Romanian and
       Azerbaijani reviews, -/fr held a Vietnamese one. Detect from the text.

NOT COLLECTED
    Dropped at scrape time: userName, userImage (Play), author.name,
    author.uri (Apple) — personal data of identifiable people, many of them EU
    residents, carrying no classification signal.
    Unavailable from either store: reviewer email, device model, the user's
    real country, purchase history.

REDACTED BEFORE THIS STAGE
    Both text and official_reply arrive with people replaced by placeholders:
    [Name] a customer, [Agent] a support agent, [Advisor] a platform psychic,
    plus [Handle], [BirthDate], [BirthTime], [Address]. Kept on purpose:
    disclosures of health, sexuality and religion, which carry the complaint
    and identify nobody alone. See the Redaction section of common.py.

Usage:
    python data/collect/scripts/normalize.py [--since YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from datetime import datetime

from common import CORPUS, RAW_APPSTORE, RAW_GOOGLEPLAY

REPLY_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TICKET_MIN_CHARS = 150          # below this a review is too short to be a ticket body

EMAIL = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w+")
VALID_CHANNELS = {
    "support-googleplay@asknebula.com", "support-appstore@asknebula.com",
    "support-trustpilot@asknebula.com", "support.nebula@gen.tech",
    "nebula.support@nebulahoroscope.com", "support@nebulahoroscope.com",
}


def _clean_date(value):
    """Scrapes stored dates via str(), so None became the string "None",
    which would otherwise pass as a non-empty date ("None"[:10] == "None")."""
    return None if not value or value == "None" else value


def parse_appstore(path: str) -> list[dict]:
    """Read one App Store country dump.

    Country comes from inside the file rather than its name: filenames are
    easily lost when files move, and provenance belongs in the data.

    Developer replies arrive here since the scraper moved off the RSS feed onto
    Apple's own proxy API. app_version and thumbs_up do not: the proxy does not
    expose them, which is the one thing RSS had and this does not.
    """
    document = json.load(open(path, encoding="utf-8"))
    country = document.get("country") or os.path.basename(path).split("_")[0]

    rows = []
    for r in document.get("reviews", []):
        latency = None
        if r.get("reply") and r.get("reply_date") and r.get("date"):
            try:
                latency = int((
                    datetime.fromisoformat(r["reply_date"].replace("Z", "+00:00"))
                    - datetime.fromisoformat(r["date"].replace("Z", "+00:00"))
                ).total_seconds())
            except ValueError:
                latency = None

        rows.append({
            "uid": "as:" + str(r.get("id")),
            "store": "appstore",
            "locale": f"-/{country}",
            "score": int(r.get("rating", 0)),
            "title": r.get("title", ""),
            "text": r.get("text") or "",
            "date": (r.get("date") or "")[:10],
            "app_version": None,           # not exposed by the proxy API
            "thumbs_up": 0,                # likewise
            "official_reply": r.get("reply") or None,
            "reply_date": (r.get("reply_date") or "")[:10] or None,
            "reply_latency_sec": latency,
            "sampled_with_filter": None,
        })
    return rows


def parse_gplay(path: str) -> list[dict]:
    """Read one Google Play language dump.

    Names in support replies are already redacted to [Name] by the scraper,
    so no PII reaches this stage.
    """
    document = json.load(open(path, encoding="utf-8"))
    lang = document.get("lang") or os.path.basename(path)[:-len(".json")]
    country = document.get("country", "us")
    sampled = document.get("sampled_with_filter")

    rows = []
    for r in document.get("reviews", []):
        latency = None
        if r.get("reply") and _clean_date(r.get("repliedAt")):
            try:
                latency = int((
                    datetime.strptime(r["repliedAt"], REPLY_TIME_FORMAT)
                    - datetime.strptime(r["at"], REPLY_TIME_FORMAT)
                ).total_seconds())
            except ValueError:
                latency = None

        rows.append({
            "uid": "gp:" + r["reviewId"][:12],
            "store": "googleplay",
            "locale": f"{lang}/{country}",
            "score": r["score"],
            "title": None,             # Google Play has no titles
            "text": r.get("content") or "",
            "date": r["at"][:10],
            "app_version": r.get("version"),
            "thumbs_up": r.get("thumbsUp", 0),
            "official_reply": r.get("reply") or None,
            "reply_date": (_clean_date(r.get("repliedAt")) or "")[:10] or None,
            "reply_latency_sec": latency,
            "sampled_with_filter": sampled,
        })
    return rows


def enrich(row: dict) -> dict:
    """Add the four derived fields."""
    row["chars"] = len(row["text"])
    row["is_complaint"] = row["score"] <= 2
    row["usable_as_ticket"] = row["chars"] >= TICKET_MIN_CHARS
    found = EMAIL.findall(row["official_reply"] or "")
    row["reply_channel"] = found[0].lower() if found else None
    row["reply_channel_valid"] = (
        row["reply_channel"] in VALID_CHANNELS if row["reply_channel"] else None
    )
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--since", metavar="YYYY-MM-DD",
                        help="keep only reviews on or after this date. Applied "
                             "after parsing, so the cutoff is exact regardless "
                             "of how the scrapers paginated.")
    args = parser.parse_args()

    appstore_files = sorted(glob.glob(os.path.join(RAW_APPSTORE, "*.json")))
    gplay_files = sorted(glob.glob(os.path.join(RAW_GOOGLEPLAY, "*.json")))
    # Natural pulls first — see READ ORDER MATTERS above.
    gplay_files.sort(key=lambda p: json.load(
        open(p, encoding="utf-8")).get("sampled_with_filter") is not None)

    rows = []
    for path in appstore_files:
        rows += parse_appstore(path)
    for path in gplay_files:
        rows += parse_gplay(path)
    print(f"read {len(appstore_files)} App Store files, "
          f"{len(gplay_files)} Google Play languages -> {len(rows)} records")

    if args.since:
        before = len(rows)
        rows = [r for r in rows if r["date"] >= args.since]
        print(f"  --since {args.since}: {before} -> {len(rows)}")

    seen, unique = set(), []
    for row in rows:
        if row["uid"] in seen:
            continue
        seen.add(row["uid"])
        unique.append(enrich(row))

    with open(CORPUS, "w", encoding="utf-8") as handle:
        for row in unique:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    broken = [r for r in unique if r["reply_channel_valid"] is False]
    print(f"corpus.jsonl: {len(unique)} records")
    print(f"  complaints (<=2 stars) : "
          f"{sum(1 for r in unique if r['is_complaint'])}")
    print(f"  usable as ticket body  : "
          f"{sum(1 for r in unique if r['is_complaint'] and r['usable_as_ticket'])}")
    print(f"  with a support reply   : "
          f"{sum(1 for r in unique if r['official_reply'])}")
    print(f"  BROKEN support address : {len(broken)}")
    for row in broken[:12]:
        print(f"     {row['uid']}  ->  {row['reply_channel']}")


if __name__ == "__main__":
    main()
