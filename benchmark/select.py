"""Pick the tickets the retrieval benchmark runs on, and write them out.

    Run: python benchmark/select.py

WHAT THIS FOLDER DECIDES
    Three questions, one measurement, because the queries are identical for all
    of them and measuring them apart would compare sets of queries rather than
    designs:

        chunking   article (73 chunks) or section (131)
        encoder    baai/bge-m3, openai/text-embedding-3-small, qwen3-embedding-8b
        retrieval  BM25, dense, or the two fused

WHY REAL TICKET TEXT AND NOT TRANSLATIONS
    An earlier plan was to translate 50 tickets into ten languages so that
    language would be the only variable. Dropped on the engineer's call, and he
    is right: 417 tickets already arrive in 12 languages written by the people
    who were actually charged, and a machine translation measures the
    translator as much as the encoder. The cost is that language is no longer
    isolated - a Spanish ticket differs from an English one in subject as well
    as in language - so per-language numbers are reportable for es (89), pt (35)
    and fr (27) and are anecdotes for the rest.

WHAT THE STORE PREFIX BUYS
    `as:` is an App Store review, `gp:` is Google Play. That decides routing,
    not just provenance: an App Store refund is Apple's decision, Google Play
    and web are support's, and the cancellation article gives DIFFERENT steps
    per rail. So for a cancellation ticket the correct section is knowable
    without a human: #1 for as:, #3 for gp:.

    It is a strong prior and not ground truth. Someone who subscribed on the
    website can still leave an App Store review - the help centre has a whole
    article about that confusion - so a ticket whose text names another rail is
    flagged here rather than assumed.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import kb                                    # noqa: E402

TICKETS = ROOT / "data" / "tickets" / "tickets.csv"
OUT = Path(__file__).resolve().parent / "tickets.csv"

# The shortlist per category lives in app/kb.py, with the knowledge base it
# describes, so that there is one table and not two to keep in step.
BY_CATEGORY = kb.ANSWERS

# Next steps that say, in the engineer's own labelling, that this ticket is not
# something the knowledge base can close. They are kept on purpose: the
# threshold below which the assistant must say "no grounded answer" cannot be
# chosen without tickets that have none.
NO_KB_STEPS = {"escalate_to_authority_case", "route_to_human_review"}

RAIL = {"appstore": "App Store", "googleplay": "Google Play"}
# A ticket whose text names a rail other than the store it was posted on. The
# cancellation steps differ per rail, so this is the case where the store
# prefix would send retrieval to the wrong section.
OTHER_RAIL = {
    "appstore": re.compile(r"google play|play store|android|веб-?сайт|website|"
                           r"asknebula\.com", re.I),
    "googleplay": re.compile(r"app ?store|apple|itunes|iphone|ipad|ios", re.I),
}


def main() -> None:
    docs = {d.id: d for d in kb.indexed(kb.verify())}
    rows = list(csv.DictReader(TICKETS.open(encoding="utf-8-sig"), delimiter=";"))

    out: list[dict] = []
    for row in rows:
        category = row["категорія"].strip()
        step = row["наступний крок"].strip()
        store = row["магазин"].strip()
        expects_none = step in NO_KB_STEPS
        shortlist = [] if expects_none else BY_CATEGORY.get(category, [])
        if not shortlist and not expects_none:
            continue

        text = f"{row['заголовок']} {row['оригінал']} {row['українською']}"
        mismatch = bool(OTHER_RAIL.get(store, re.compile(r"(?!)")).search(text))
        out.append({
            "id": row["id"],
            "store": store,
            "rail": RAIL.get(store, ""),
            "rail_uncertain": "yes" if mismatch else "",
            "lang": row["мова"],
            "category": category,
            "priority": row["пріоритет"].strip(),
            "next_step": step,
            "expects_none": "yes" if expects_none else "",
            "shortlist": " ".join(shortlist),
            "gold": "",          # filled by hand: article ids, or "none"
            "title": row["заголовок"],
            "original": row["оригінал"],
            "ua": row["українською"],
        })

    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(out)

    import collections
    print(f"{len(out)} tickets -> {OUT.relative_to(ROOT)}")
    print("  by category:",
          dict(collections.Counter(r["category"] for r in out).most_common()))
    print("  by store:   ", dict(collections.Counter(r["store"] for r in out)))
    print("  by language:",
          dict(collections.Counter(r["lang"] for r in out).most_common()))
    print("  expecting no KB answer:",
          sum(1 for r in out if r["expects_none"]))
    print("  rail uncertain (text names another rail):",
          sum(1 for r in out if r["rail_uncertain"]))
    unknown = {a for ids in BY_CATEGORY.values() for a in ids} - set(docs)
    if unknown:
        raise SystemExit("shortlist names documents not in the index: "
                         + ", ".join(sorted(unknown)))


if __name__ == "__main__":
    main()
