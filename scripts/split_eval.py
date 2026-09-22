"""Split the 417 labelled tickets into three sets with the SAME mix of themes.

    data/sets/fewshot_v1.json    25 rows -- the examples that sit inside the prompt
    data/sets/dev_v1.json       157 rows -- iterate here, read failures here
    data/sets/golden_v1.json    235 rows -- frozen; scores every prompt version
    data/sets/manifest_v1.json          -- quotas, method, composition achieved

WHY AN EVEN MIX AND NOT THREE ARBITRARY SLICES
    If few-shot were all billing and dev mostly bugs, every number would be
    unreadable: a drop on dev would say nothing about the prompt and everything
    about the draw.  So the split is stratified on the label triple plus the
    language, and each stratum is dealt across the three sets in proportion.

THE METHOD IS APPORTIONMENT, NOT SAMPLING
    Rows are sorted so that near-identical tickets stand next to each other,
    then walked once.  Each row goes to the set with the highest quotient
    quota / (assigned + 0.5) -- Webster's method -- among the sets not yet
    full.  There is no random seed anywhere: the same csv always produces the
    same three files, byte for byte.

TWO RULES THAT OVERRIDE PROPORTION
    1. Template twins travel together.  Two pairs of tickets in this corpus are
       the same letter with a different sum.  Split across files, one would be
       teaching the prompt and the other grading it.  A pair is dealt as one
       unit, and never into few-shot -- a duplicate there wastes a slot.
    2. Few-shot must show every category at least once, `other` included.
       Nine rows of `other` against 417 round to half a slot, so the draw is
       corrected by one swap with dev, and the manifest records it.
    3. Step coverage.  Proportion is exactly wrong here: with 25 slots, a step
       holding 1.0-1.4% of the corpus rounds to zero, so the three rarest steps
       got no example at all -- including the one carrying the only hard rule in
       the schema (escalate_to_authority_case forces P1) and the one that IS the
       human-in-the-loop deliverable.  A value the prompt must produce and never
       shows is decided by prose alone, and with one row each in dev a mistake
       would not even surface until golden.  So every step with 3+ rows in the
       corpus gets one few-shot example, taken from the most crowded step.  The
       swap is against DEV ONLY, never golden, so the frozen set stays
       byte-identical and can be frozen before this rule is even settled.
    4. Language presence.  The sort key is the label triple, so language is
       balanced only as a side effect -- and the first run left golden without a
       single Arabic ticket while few-shot had no French one.  Every language
       with 3+ rows must appear in golden, every language with 10+ rows must
       appear in few-shot, and both are fixed by swapping against a row with
       the IDENTICAL label triple, which leaves the label composition of both
       files untouched.  Every trade is listed in the manifest.

NOT INCLUDED, DELIBERATELY
    The 15 synthetic cases (aggressive tone, mixed topic, non-English, empty
    input, injection attempt) are written by hand and land in golden as a
    separate file.  They cannot come out of this csv -- nothing in the corpus
    tries to hijack the classifier.
"""
from __future__ import annotations

import collections
import csv
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "tickets", "tickets.csv")
OUT_DIR = os.path.join(ROOT, "data", "sets")

QUOTAS = {"fewshot": 25, "dev": 157, "golden": 235}          # sums to 417

# Two letters sent twice from the same template, found while labelling.
TWINS = [("as:14334387664", "as:14466218468"),
         ("gp:14528ce0-b72", "gp:bceaf4ac-614")]

# Languages with fewer than ~10 rows cannot be a stratum of their own; they
# would round to zero everywhere.  Collapsed, they still get dealt evenly.
MAIN_LANGS = {"en_or_unknown", "es", "pt", "fr", "de", "tr"}

LABELS = ("категорія", "пріоритет", "наступний крок")
BASECOLS = ("id", "партія", "дата", "зірки", "магазин", "мова",
            "заголовок", "оригінал", "українською")


def lang_bucket(row):
    return row["мова"] if row["мова"] in MAIN_LANGS else "other_lang"


def stratum(row):
    return (row["категорія"], row["наступний крок"], row["пріоритет"],
            lang_bucket(row))


def read_rows():
    with io.open(SRC, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def deal(units):
    """Webster apportionment over a sorted list of units (1 or 2 rows each)."""
    assigned = {k: [] for k in QUOTAS}
    count = {k: 0 for k in QUOTAS}
    for unit in units:
        need = len(unit)
        room = [k for k in QUOTAS if count[k] + need <= QUOTAS[k]]
        if need > 1:                                   # rule 1: no pairs in few-shot
            room = [k for k in room if k != "fewshot"] or room
        pick = max(room, key=lambda k: (QUOTAS[k] / (count[k] + 0.5), k))
        assigned[pick].extend(unit)
        count[pick] += need
    return assigned


def fix_category_coverage(assigned):
    """Rule 2: every category visible in few-shot, swapping against dev only."""
    swaps = []
    in_few = collections.Counter(r["категорія"] for r in assigned["fewshot"])
    all_cats = {r["категорія"] for v in assigned.values() for r in v}
    for cat in sorted(all_cats):
        if in_few[cat]:
            continue
        donor_cat = in_few.most_common(1)[0][0]        # the most crowded one
        out = next(r for r in assigned["fewshot"] if r["категорія"] == donor_cat)
        into = next(r for r in assigned["dev"] if r["категорія"] == cat)
        assigned["fewshot"].remove(out)
        assigned["dev"].remove(into)
        assigned["fewshot"].append(into)
        assigned["dev"].append(out)
        in_few[donor_cat] -= 1
        in_few[cat] += 1
        swaps.append({"into_fewshot": into["id"], "category_gained": cat,
                      "out_to_dev": out["id"], "category_given_up": donor_cat})
    return swaps


def fix_step_coverage(assigned, rows):
    """Rule 3: a few-shot example for every step, swapping against dev only.

    Guarded so it cannot undo the other two rules: the row given away is never
    the only one of its category in few-shot, and never the only one of a
    language that has ten or more rows in the corpus.
    """
    swaps = []
    pop = collections.Counter(r["наступний крок"] for r in rows)
    lang_pop = collections.Counter(r["мова"] for r in rows)
    for step in sorted(pop, key=lambda s: (pop[s], s)):        # rarest first
        if pop[step] < 3:
            continue
        few_steps = collections.Counter(r["наступний крок"]
                                        for r in assigned["fewshot"])
        if few_steps[step]:
            continue
        cats = collections.Counter(r["категорія"] for r in assigned["fewshot"])
        langs = collections.Counter(r["мова"] for r in assigned["fewshot"])
        donor_step = few_steps.most_common(1)[0][0]
        out = None
        for r in assigned["fewshot"]:
            if r["наступний крок"] != donor_step:
                continue
            if cats[r["категорія"]] <= 1:                      # keeps rule 1
                continue
            if lang_pop[r["мова"]] >= 10 and langs[r["мова"]] <= 1:
                continue                                       # keeps rule 4
            out = r
            break
        into = next((r for r in assigned["dev"]
                     if r["наступний крок"] == step), None)
        if out is None or into is None:
            swaps.append({"step": step, "result": "no safe partner in dev"})
            continue
        assigned["fewshot"].remove(out)
        assigned["dev"].remove(into)
        assigned["fewshot"].append(into)
        assigned["dev"].append(out)
        swaps.append({"step_gained": step, "into_fewshot": into["id"],
                      "out_to_dev": out["id"], "step_given_up": donor_step,
                      "category_in": into["категорія"],
                      "category_out": out["категорія"]})
    return swaps


def fix_language_presence(assigned, rows):
    """Rule 3: label-neutral swaps so no file is blind to a whole language."""
    trades = []
    pop = collections.Counter(r["мова"] for r in rows)
    wanted = [("golden", 3), ("fewshot", 10)]
    for target, floor in wanted:
        for lang in sorted(pop, key=lambda x: (-pop[x], x)):
            if not lang or pop[lang] < floor:
                continue
            if any(r["мова"] == lang for r in assigned[target]):
                continue
            donors = [n for n in assigned if n != target
                      and any(r["мова"] == lang for r in assigned[n])]
            if not donors:
                continue
            # dev first, always: golden is the frozen set, and a rule that can
            # reach into it makes the freeze depend on every other rule's order
            donor = ("dev" if "dev" in donors
                     else max(donors, key=lambda n: sum(
                         1 for r in assigned[n] if r["мова"] == lang)))
            incoming = next(r for r in assigned[donor] if r["мова"] == lang)
            triple = tuple(incoming[k] for k in LABELS)
            match = next((r for r in assigned[target]
                          if tuple(r[k] for k in LABELS) == triple
                          and r["мова"] != lang), None)
            relaxed = False
            if match is None:                  # no exact triple: keep the cause
                match = next((r for r in assigned[target]
                              if (r["категорія"], r["наступний крок"])
                              == triple[:2] and r["мова"] != lang), None)
                relaxed = match is not None
            if match is None:
                trades.append({"target": target, "language": lang,
                               "result": "no label-neutral partner, left as is"})
                continue
            assigned[donor].remove(incoming)
            assigned[target].remove(match)
            assigned[target].append(incoming)
            assigned[donor].append(match)
            trades.append({
                "target": target, "language": lang, "from": donor,
                "in": incoming["id"], "out": match["id"],
                "label_triple": " / ".join(triple),
                "priority_moved": relaxed and match["пріоритет"] != triple[1],
            })
    return trades


def shape(row):
    out = {k: row[k] for k in BASECOLS}
    out["розмітка"] = {k: row[k] for k in LABELS}
    out["нотатка"] = row["нотатка"]
    return out


def composition(rows, key):
    c = collections.Counter(key(r) for r in rows)
    return {k: c[k] for k in sorted(c, key=lambda x: (-c[x], x))}


def main():
    rows = read_rows()
    by_id = {r["id"]: r for r in rows}

    paired = {u for pair in TWINS for u in pair}
    units = [[by_id[a], by_id[b]] for a, b in TWINS]
    units += [[r] for r in rows if r["id"] not in paired]
    units.sort(key=lambda u: (stratum(u[0]), u[0]["id"]))

    assigned = deal(units)
    swaps = fix_category_coverage(assigned)
    steps = fix_step_coverage(assigned, rows)
    trades = fix_language_presence(assigned, rows)

    for name in assigned:
        assigned[name].sort(key=lambda r: (r["партія"], r["id"]))

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    for name, rs in assigned.items():
        path = os.path.join(OUT_DIR, "%s_v1.json" % name)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps([shape(r) for r in rs], ensure_ascii=False,
                                indent=2))
            fh.write("\n")

    dims = {"категорія": lambda r: r["категорія"],
            "пріоритет": lambda r: r["пріоритет"],
            "наступний крок": lambda r: r["наступний крок"],
            "мова": lambda r: r["мова"],
            "магазин": lambda r: r["магазин"]}
    manifest = {
        "source": os.path.relpath(SRC, ROOT).replace("\\", "/"),
        "source_rows": len(rows),
        "method": "Webster apportionment over strata sorted by "
                  "(категорія, наступний крок, пріоритет, lang_bucket); "
                  "no randomness, byte-identical on re-run",
        "quotas": QUOTAS,
        "twins_kept_together": [list(p) for p in TWINS],
        "fewshot_coverage_swaps": swaps,
        "fewshot_step_coverage_swaps": steps,
        "language_presence_trades": trades,
        "composition": {name: {d: composition(rs, f) for d, f in dims.items()}
                        for name, rs in assigned.items()},
    }
    with io.open(os.path.join(OUT_DIR, "manifest_v1.json"), "w",
                 encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=2))
        fh.write("\n")

    # -- console report: the point is that the three columns look alike -------
    order = ("fewshot", "dev", "golden")
    print("рядків: %d   %s" % (len(rows), "  ".join(
        "%s=%d" % (n, len(assigned[n])) for n in order)))
    for dim, f in dims.items():
        print("\n-- %s (частка всередині кожного файлу)" % dim)
        vals = collections.Counter(f(r) for r in rows)
        print("   %-28s %8s %8s %8s %8s" % ("", "усього", *order))
        for v in sorted(vals, key=lambda x: (-vals[x], x)):
            cells = []
            for n in order:
                k = sum(1 for r in assigned[n] if f(r) == v)
                cells.append("%3d %4.1f%%" % (k, 100.0 * k / len(assigned[n])))
            print("   %-28s %4d %4.1f%%  %s"
                  % (v or "(порожня)", vals[v], 100.0 * vals[v] / len(rows),
                     " ".join(cells)))
    for s in swaps:
        print("\nswap для покриття категорій: %s -> fewshot (%s), %s -> dev"
              % (s["into_fewshot"], s["category_gained"], s["out_to_dev"]))
    for s in steps:
        if "into_fewshot" not in s:
            print("\nкрок %s: %s" % (s["step"], s["result"]))
            continue
        print("\nswap за кроком: %s -> fewshot (%s), назад %s (%s); golden не "
              "торкались" % (s["into_fewshot"], s["step_gained"],
                             s["out_to_dev"], s["step_given_up"]))
    for t in trades:
        if "in" not in t:
            print("\nмова %s у %s: %s" % (t["language"], t["target"],
                                          t["result"]))
            continue
        print("\nобмін за мовою: %s (%s) %s -> %s, назад %s; мітки ті самі (%s)"
              % (t["in"], t["language"], t["from"], t["target"], t["out"],
                 t["label_triple"]))
    print("\nфайли в %s" % os.path.relpath(OUT_DIR, ROOT))


if __name__ == "__main__":
    main()
