"""Draw two disjoint ticket sets from the corpus, against explicit cells.

    data/tickets/golden.json     100 rows, frozen: the evaluation set
    data/tickets/dev.json        100 rows, free to iterate on
    data/tickets/considered.json every id the draw weighed
    data/tickets/manifest.json   the parameters and the composition actually
                                 achieved, including every cell that could not
                                 be filled

    Indented JSON throughout, not JSONL. These files exist to be read and
    argued about by people; a 400-character ticket and its label on one line
    cannot be reviewed.

ORDER MATTERS AND IT IS NOT NEGOTIABLE
    Golden is drawn first and removed from the pool; only then is dev drawn.
    That makes contamination structurally impossible instead of something to
    check for afterwards.

THREE STREAMS, BECAUSE ONE CANNOT REACH EVERYTHING
    main         the 1,192 rows that pass every criterion in criteria.py
    language     non-English rows, drawn on length and script alone. The ASK
                 and PROBLEM lexicons are Latin-script, so a Japanese ticket
                 fails them however clearly it asks for a refund.
    supplement   rows OUTSIDE the twelve-month window, for themes the window
                 leaves almost empty. Measured: advisor_conduct has 5 rows in
                 the window against 11 in the corpus, account_access 2 against
                 21, data_privacy 3 against 12. The assignment names complaints
                 about experts as one of four themes, so a set holding three of
                 them cannot measure it. Every supplement row carries
                 in_window=false and the manifest counts them, so the freshness
                 criterion is bent visibly rather than quietly.

WHY THE CELLS ARE UNEVEN
    They are capped by what exists. A proportional sample of 100 would be
    almost entirely billing and nothing else: 767 of the 1,192 pool rows touch
    a billing theme, 64.3%, and refunds alone are 35.2%. The cells below spend
    the scarce slots on the themes the assignment names and on the edge cases
    it asks for.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import criteria as C                                              # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "data", "corpus.jsonl")
OUT_DIR = os.path.join(ROOT, "data", "tickets")

# --- the cells, per set of 100 ----------------------------------------------
# A cell is a question the evaluation must be able to answer. An empty cell is
# reported, never silently redistributed.
THEME_CELLS: dict[str, int] = {
    "refund_request": 6,
    "trial_converted": 5,
    "unauthorized_charge": 5,
    "cancellation_failed": 5,
    "pricing_unclear": 2,
    "service_not_delivered": 2,
    # 4, not 3: the slot freed when advisor_conduct stopped being a category on
    # 2026-09-21 goes here. It goes to content_quality rather than back into the
    # billing cells because the billing cells are the ones that do NOT survive
    # labelling - six refund_request slots produced one refund_request label,
    # since the probe fires on the demand and the rule assigns the cause - while
    # content_quality rows keep their category once a human reads them, and the
    # corpus holds 16 of them against an allocation of 3.
    "content_quality": 4,
    "app_technical": 3,           # "bugs" in the assignment's own wording
    "data_privacy": 1,
}
# Rows no probe recognises. They are not noise: they are the 34% of the pool
# whose subject the sampler cannot name, which makes them the honest test of
# whether a classifier reaches for `other` or invents a category.
UNKNOWN_CELL = 4
NON_LATIN_CELL = 4        # one or two per script, capped by what exists
LATIN_NON_ENGLISH_CELL = 6

# Two to four stars: the merely dissatisfied. Without this cell the sets come
# out 94% one-star, because the corpus rating distribution is U-shaped and
# dropping five stars leaves the furious. That is not the population a support
# queue sees. Measured, these rows sound different in a way that matters - a
# four-star "it would exit without loading, please help to fix this" is a plain
# bug report, and bug reports are one of the four themes the assignment names.
# 86 such rows exist in the main pool and 107 in the language pool.
MILD_STARS_CELL = 3
MILD_STARS = frozenset({2, 3, 4})
SET_SIZE = 50

# The plan must sum to the set size. A first version added up to 110 and the
# final `rows[:SET_SIZE]` silently dropped the overflow - which was the LAST
# cell filled, `unknown`, the one criterion F depends on. The set came out with
# zero of them and nothing said so. An assertion at import is the cheap fix.
PLANNED = (sum(THEME_CELLS.values()) + UNKNOWN_CELL + NON_LATIN_CELL
           + LATIN_NON_ENGLISH_CELL + MILD_STARS_CELL)
assert PLANNED == SET_SIZE, (
    f"the cells plan {PLANNED} rows for a set of {SET_SIZE}: "
    f"themes {sum(THEME_CELLS.values())}, unknown {UNKNOWN_CELL}, "
    f"non-Latin {NON_LATIN_CELL}, Latin non-English {LATIN_NON_ENGLISH_CELL}, "
    f"mild stars {MILD_STARS_CELL}")

# Themes scarce enough in the window that the supplement is allowed to reach
# outside it. Anything not listed here is window-only.
SUPPLEMENT_ALLOWED = frozenset({
    "data_privacy", "app_technical", "content_quality",
})

LATIN_ORDER = ["es", "pt", "fr", "it", "de", "tr", "nl", "pl"]
SCRIPT_ORDER = ["han", "kana", "cyrillic", "arabic", "thai", "hebrew",
                "hangul", "greek"]


def text_hash(text: str) -> str:
    return hashlib.sha256(C.normalise(text).casefold().encode("utf-8")).hexdigest()


def to_ticket(row: dict, cell: str, in_window: bool) -> dict:
    """One record, with input and provenance kept apart.

    `text` is the only field the classifier will ever see. `provenance` holds
    store, locale, star and the official reply: all four would help a model and
    none of them exists in the real support form, so accuracy bought with them
    would evaporate on deployment.
    """
    text = row["text"]
    probes = C.probes_for(text)
    coverage, articles = C.kb_coverage(probes)
    language = C.guess_language(text)
    return {
        "ticket_id": row["uid"],
        "text": text,
        "text_sha256": text_hash(text),
        "chars": len(text),
        "selection": {
            "cell": cell,
            "in_window": in_window,
            "probes": probes,
            # A GUESS, and named as one. It is computed from the probes, whose
            # recall is 69%, so a row the sampler cannot read comes out
            # `unknown` - which describes the instrument, not the knowledge
            # base. The decidable answer is attached to the label instead, by
            # apply_labels.py, once a human has named the subject. Measured on
            # the golden set: 25 of the 29 `unknown` rows turned out covered.
            "kb_coverage_guess": coverage,
            "kb_articles_guess": articles,
            "language": language,
            "flags": {
                "aggressive": bool(C.AGGRESSIVE.search(text)),
                "multi_topic": len(probes) > 1,
                "non_english": language != "en_or_unknown",
                "non_latin_script": bool(C.NON_LATIN.search(text)),
            },
        },
        "provenance": {
            "store": row.get("store"),
            "locale": row.get("locale"),
            "score": row.get("score"),
            "date": row.get("date"),
            "title": row.get("title"),
            "official_reply": row.get("official_reply"),
            "reply_latency_sec": row.get("reply_latency_sec"),
        },
        "label": None,
    }


def take(candidates: list[dict], count: int, taken: set[str],
         rng: random.Random, seen_hashes: set[str]) -> list[dict]:
    """Draw `count` rows at random, skipping anything already used.

    Deduplication is by normalised text, not by id: the same complaint is
    posted to both stores, and a duplicate across golden and dev is leakage.
    """
    free = [r for r in candidates
            if r["uid"] not in taken and text_hash(r["text"]) not in seen_hashes]
    rng.shuffle(free)
    chosen: list[dict] = []
    for row in free:
        if len(chosen) >= count:
            break
        digest = text_hash(row["text"])
        if digest in seen_hashes:
            continue
        chosen.append(row)
        taken.add(row["uid"])
        seen_hashes.add(digest)
    return chosen


def build_set(name: str, main: list[dict], language: list[dict],
              outside: list[dict], taken: set[str], seen: set[str],
              rng: random.Random) -> tuple[list[dict], list[dict]]:
    """Fill the cells in order of scarcity: what cannot be refilled goes first."""
    rows: list[dict] = []
    shortfalls: list[dict] = []

    def record(cell: str, wanted: int, got: int) -> None:
        if got < wanted:
            shortfalls.append({"set": name, "cell": cell,
                               "wanted": wanted, "got": got})

    # 1. Non-Latin scripts. Scarcest of all - 3 Hangul rows exist in the
    #    window, so this cell is the whole population, not a sample.
    per_script = max(1, NON_LATIN_CELL // len(SCRIPT_ORDER))
    script_rows: list[dict] = []
    for script in SCRIPT_ORDER:
        if len(script_rows) >= NON_LATIN_CELL:
            break
        pool = [r for r in language if C.guess_language(r["text"]) == script]
        script_rows += take(pool, per_script, taken, rng, seen)
    if len(script_rows) < NON_LATIN_CELL:                 # fill from any script
        pool = [r for r in language if C.NON_LATIN.search(r["text"])]
        script_rows += take(pool, NON_LATIN_CELL - len(script_rows), taken, rng, seen)
    record("non_latin_script", NON_LATIN_CELL, len(script_rows))
    rows += [to_ticket(r, f"lang:{C.guess_language(r['text'])}", True) for r in script_rows]

    # 2. Latin non-English, one or two per language.
    per_language = max(1, LATIN_NON_ENGLISH_CELL // len(LATIN_ORDER))
    latin_rows: list[dict] = []
    for code in LATIN_ORDER:
        if len(latin_rows) >= LATIN_NON_ENGLISH_CELL:
            break
        pool = [r for r in language if C.guess_language(r["text"]) == code]
        latin_rows += take(pool, per_language, taken, rng, seen)
    if len(latin_rows) < LATIN_NON_ENGLISH_CELL:
        pool = [r for r in language
                if C.guess_language(r["text"]) in LATIN_ORDER]
        latin_rows += take(pool, LATIN_NON_ENGLISH_CELL - len(latin_rows),
                           taken, rng, seen)
    record("latin_non_english", LATIN_NON_ENGLISH_CELL, len(latin_rows))
    rows += [to_ticket(r, f"lang:{C.guess_language(r['text'])}", True) for r in latin_rows]

    # 3. The merely dissatisfied, before the theme cells: 31 rows exist in the
    #    main pool, so a later cell would swallow them by accident.
    mild_rows = take([r for r in main if r.get("score") in MILD_STARS],
                     MILD_STARS_CELL, taken, rng, seen)
    if len(mild_rows) < MILD_STARS_CELL:
        mild_rows += take([r for r in language if r.get("score") in MILD_STARS],
                          MILD_STARS_CELL - len(mild_rows), taken, rng, seen)
    record("mild_stars_2_to_4", MILD_STARS_CELL, len(mild_rows))
    rows += [to_ticket(r, "mild_stars", True) for r in mild_rows]

    # 4. Themes, rarest first, with the supplement only where it is allowed.
    for theme, wanted in sorted(THEME_CELLS.items(), key=lambda kv: kv[1]):
        pool = [r for r in main if theme in C.probes_for(r["text"])]
        got = take(pool, wanted, taken, rng, seen)
        rows += [to_ticket(r, theme, True) for r in got]
        if len(got) < wanted and theme in SUPPLEMENT_ALLOWED:
            extra_pool = [r for r in outside if theme in C.probes_for(r["text"])]
            extra = take(extra_pool, wanted - len(got), taken, rng, seen)
            rows += [to_ticket(r, f"supplement:{theme}", False) for r in extra]
            got = got + extra
        record(theme, wanted, len(got))

    # 5. Rows no probe recognises.
    unknown_pool = [r for r in main if not C.probes_for(r["text"])]
    unknown = take(unknown_pool, UNKNOWN_CELL, taken, rng, seen)
    record("unknown", UNKNOWN_CELL, len(unknown))
    rows += [to_ticket(r, "unknown", True) for r in unknown]

    # 6. Top up to the set size from whatever the main pool has left.
    if len(rows) < SET_SIZE:
        filler = take(main, SET_SIZE - len(rows), taken, rng, seen)
        rows += [to_ticket(r, "top_up", True) for r in filler]
    record("set_size", SET_SIZE, len(rows))
    if len(rows) > SET_SIZE:
        # Should be unreachable - PLANNED is asserted at import - but if a cell
        # ever overfills, say which rows are being dropped instead of slicing.
        dropped = collections.Counter(r["selection"]["cell"] for r in rows[SET_SIZE:])
        shortfalls.append({"set": name, "cell": "OVERFILL",
                           "wanted": SET_SIZE, "got": len(rows),
                           "dropped": dict(dropped)})
    return rows[:SET_SIZE], shortfalls


def describe(name: str, rows: list[dict]) -> dict:
    sel = [r["selection"] for r in rows]
    flags = collections.Counter(k for s in sel for k, v in s["flags"].items() if v)
    summary = {
        "rows": len(rows),
        "stores": dict(collections.Counter(r["provenance"]["store"] for r in rows)),
        "stars": dict(sorted(collections.Counter(
            r["provenance"]["score"] for r in rows).items())),
        "in_window": sum(1 for s in sel if s["in_window"]),
        "out_of_window": sum(1 for s in sel if not s["in_window"]),
        "kb_coverage_guess": dict(collections.Counter(
            s["kb_coverage_guess"] for s in sel)),
        "flags": dict(flags),
        "languages": dict(collections.Counter(s["language"] for s in sel).most_common()),
        "cells": dict(collections.Counter(s["cell"] for s in sel).most_common()),
        "chars_p50": sorted(r["chars"] for r in rows)[len(rows) // 2],
        "oldest": min(r["provenance"]["date"] for r in rows),
        "newest": max(r["provenance"]["date"] for r in rows),
    }
    print(f"\n=== {name}: {summary['rows']} rows ===")
    for key in ("stores", "stars", "kb_coverage_guess", "flags", "languages"):
        print(f"  {key:14} {summary[key]}")
    print(f"  {'window':14} in {summary['in_window']}, outside "
          f"{summary['out_of_window']}   dates {summary['oldest']}..{summary['newest']}")
    print(f"  {'chars p50':14} {summary['chars_p50']}")
    return summary


def write_json(rows: list[dict], path: str) -> None:
    """Indented JSON, not JSONL.

    JSONL is the convention for datasets and it is the right one at a million
    rows, where nothing is read by eye. At 100 rows the trade is the other way
    round: these files are going to be read and argued about by people, and a
    400-character ticket on one line with its label is not reviewable. Both
    formats load with one call; only one of them can be checked by a human.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--as-of", default=C.AS_OF_DEFAULT,
                        help="the window is measured back from this date, not from today")
    parser.add_argument("--window-days", type=int, default=C.WINDOW_DAYS)
    parser.add_argument("--seed", type=int, default=20260920)
    parser.add_argument("--dry-run", action="store_true",
                        help="report the composition without writing any file")
    args = parser.parse_args()

    if not os.path.exists(CORPUS):
        raise SystemExit(f"{CORPUS} is missing - run "
                         f"data/collect/scripts/normalize.py first")
    rows = [json.loads(line) for line in open(CORPUS, encoding="utf-8")]
    cut = C.cutoff(args.as_of, args.window_days)
    C.verify_kb_table()
    print(f"corpus {len(rows)} rows | window {cut}..{args.as_of} | seed {args.seed}")

    main_pool = [r for r in rows if C.is_ticket_shaped(r, cut)]
    language_pool = [r for r in rows
                     if r.get("date", "") >= cut
                     and r.get("score") in C.ALLOWED_STARS
                     and len(r.get("text") or "") >= 150
                     and C.ADDRESSED_TO_COMPANY.search(r["text"])
                     and not C.OPENS_AS_WARNING.search(r["text"])
                     and (C.NON_LATIN.search(r["text"])
                          or C.guess_language(r["text"]) != "en_or_unknown")]
    outside_pool = [r for r in rows
                    if r.get("date", "") < cut and C.is_ticket_shaped(r, "0000")]
    print(f"main {len(main_pool)} | language {len(language_pool)} | "
          f"outside the window {len(outside_pool)}")

    rng = random.Random(args.seed)
    taken: set[str] = set()
    seen: set[str] = set()
    golden, short_golden = build_set("golden", main_pool, language_pool,
                                    outside_pool, taken, seen, rng)
    dev, short_dev = build_set("dev", main_pool, language_pool,
                               outside_pool, taken, seen, rng)

    golden_summary = describe("golden", golden)
    dev_summary = describe("dev", dev)
    shortfalls = short_golden + short_dev
    if shortfalls:
        print("\ncells that could not be filled:")
        for item in shortfalls:
            print(f"  {item['set']:7} {item['cell']:22} wanted {item['wanted']}, "
                  f"got {item['got']}")

    overlap_ids = {r["ticket_id"] for r in golden} & {r["ticket_id"] for r in dev}
    overlap_text = {r["text_sha256"] for r in golden} & {r["text_sha256"] for r in dev}
    print(f"\nleakage check: {len(overlap_ids)} shared ids, "
          f"{len(overlap_text)} shared text hashes")
    if overlap_ids or overlap_text:
        raise SystemExit("golden and dev overlap - refusing to write")

    if args.dry_run:
        print("\ndry run: nothing written")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    write_json(golden, os.path.join(OUT_DIR, "golden.json"))
    write_json(dev, os.path.join(OUT_DIR, "dev.json"))
    write_json([{"ticket_id": r["uid"], "text_sha256": text_hash(r["text"]),
                 "date": r.get("date"), "store": r.get("store")}
                for r in main_pool],
               os.path.join(OUT_DIR, "considered.json"))
    manifest = {
        "built_at_as_of": args.as_of,
        "window": {"from": cut, "to": args.as_of, "days": args.window_days},
        "seed": args.seed,
        "criteria_module": "scripts/criteria.py",
        "pools": {"main": len(main_pool), "language": len(language_pool),
                  "outside_window": len(outside_pool)},
        "cells_requested": {"themes": THEME_CELLS, "unknown": UNKNOWN_CELL,
                            "non_latin_script": NON_LATIN_CELL,
                            "latin_non_english": LATIN_NON_ENGLISH_CELL},
        "supplement_allowed": sorted(SUPPLEMENT_ALLOWED),
        "golden": golden_summary,
        "dev": dev_summary,
        "shortfalls": shortfalls,
        "leakage": {"shared_ids": len(overlap_ids), "shared_text": len(overlap_text)},
    }
    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    print(f"\nwritten to {OUT_DIR}:")
    for name in ("golden.json", "dev.json", "considered.json",
                 "manifest.json"):
        size = os.path.getsize(os.path.join(OUT_DIR, name))
        print(f"  {name:18} {size / 1024:8.1f} KB")


if __name__ == "__main__":
    main()
