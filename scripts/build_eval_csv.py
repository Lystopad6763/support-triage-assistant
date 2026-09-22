"""One table holding every ticket the system will be built on, in both formats.

    data/sets/all_v1.csv        432 rows = 417 from the corpus + 15 by hand
    data/sets/all_v1.json       the same table, for code
    data/tickets/tickets.json   the 417 labelled rows, twin of tickets.csv

The four set files are what the pipeline loads; these are views.  The csv adds
one column, `набір`, saying which set each ticket belongs to, so the split can
be read and sorted in Excel without joining anything -- and the json twins exist
because a csv open in Excel is locked against writing, which stopped a run once.

SHAPE, AND WHY IT DIFFERS FROM THE SET FILES
    Both json files are FLAT: exactly the columns of the csv they mirror, labels
    at the top level.  The set files nest the labels under `розмітка`, because
    there they are the thing being predicted.  A format twin should differ from
    its csv in nothing but syntax, so it does not inherit that nesting.

Generated, never edited: change tickets.csv or the case list, then re-run
split_eval.py, make_synthetic.py and this.  The csv is semicolon-separated and
UTF-8 with a BOM, like tickets.csv, because Excel on a Ukrainian locale
otherwise shows one mojibake column.
"""
from __future__ import annotations

import collections
import csv
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL = os.path.join(ROOT, "data", "sets")
OUT = os.path.join(EVAL, "all_v1.csv")
OUT_JSON = os.path.join(EVAL, "all_v1.json")
TIC_CSV = os.path.join(ROOT, "data", "tickets", "tickets.csv")
TIC_JSON = os.path.join(ROOT, "data", "tickets", "tickets.json")

SETS = ("fewshot", "dev", "golden", "synthetic")      # the order in the file
LABELS = ("категорія", "пріоритет", "наступний крок")
COLS = ["id", "набір", "партія", "дата", "зірки", "магазин", "мова",
        "заголовок", "оригінал", "українською"] + list(LABELS) + ["нотатка"]


def write_json(path, rows):
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(rows, ensure_ascii=False, indent=2))
        fh.write("\n")


def main():
    rows = []
    for name in SETS:
        path = os.path.join(EVAL, "%s_v1.json" % name)
        for r in json.load(io.open(path, encoding="utf-8")):
            flat = {k: r.get(k, "") for k in COLS}
            flat["набір"] = name
            flat.update(r["розмітка"])
            rows.append(flat)

    with io.open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow(COLS)
        for r in rows:
            w.writerow([r[k] for k in COLS])
    write_json(OUT_JSON, [{k: r[k] for k in COLS} for r in rows])

    # -- the source of truth, mirrored: same columns, same order, json syntax --
    with io.open(TIC_CSV, encoding="utf-8-sig") as fh:
        src = list(csv.DictReader(fh, delimiter=";"))
    write_json(TIC_JSON, src)

    print("рядків: %d   %s байт csv   %s байт json"
          % (len(rows), format(os.path.getsize(OUT), ",d"),
             format(os.path.getsize(OUT_JSON), ",d")))
    print("tickets.json: %d рядків, %d колонок, %s байт"
          % (len(src), len(src[0]), format(os.path.getsize(TIC_JSON), ",d")))
    per = collections.Counter(r["набір"] for r in rows)
    print("   " + "   ".join("%s=%d" % (n, per[n]) for n in SETS))
    for dim in ("категорія", "наступний крок", "пріоритет"):
        print("\n-- %s" % dim)
        vals = collections.Counter(r[dim] for r in rows)
        print("   %-28s %6s %s" % ("", "усього",
                                   " ".join("%8s" % n for n in SETS)))
        for v in sorted(vals, key=lambda x: (-vals[x], x)):
            cells = " ".join("%8d" % sum(1 for r in rows if r["набір"] == n
                                         and r[dim] == v) for n in SETS)
            print("   %-28s %6d %s" % (v, vals[v], cells))
    print("\nфайл: %s" % os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
