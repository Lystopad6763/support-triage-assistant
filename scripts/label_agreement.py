"""How much two independent readers of the same tickets agree.

    python scripts/label_agreement.py labels/dev/pass_a.json labels/dev/recheck.json

WHY THIS EXISTS
    "I labelled them carefully" is not a number. An evaluation set whose labels
    nobody re-derived has an unknown error floor, and every accuracy figure
    measured against it inherits that floor silently. Twenty tickets labelled
    twice, independently, from the same rubric give the floor a value.

WHAT IT REPORTS
    Raw agreement per field, and Cohen's kappa for the category. Kappa matters
    because raw agreement flatters an unbalanced set: if 40% of tickets are
    cancellation_failed, two readers who always guessed that label would agree
    16% of the time by luck alone. Kappa subtracts the luck.

HOW TO READ KAPPA
    Below 0.40 means the rubric is not decidable and needs rewriting, not more
    labellers. 0.40-0.60 is moderate. 0.60-0.80 is substantial and is the usual
    ceiling for a 13-class taxonomy with genuinely overlapping tickets. Above
    0.80 on this data would be suspicious rather than reassuring.
"""
from __future__ import annotations

import argparse
import collections
import json


def load(path: str) -> dict[str, dict]:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):                       # a list of label objects
        return {row["ticket_id"]: row for row in data}
    return data                                       # or a map keyed by id


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    """Chance-corrected agreement on a single categorical field."""
    if not pairs:
        return float("nan")
    total = len(pairs)
    observed = sum(1 for a, b in pairs if a == b) / total
    first = collections.Counter(a for a, _ in pairs)
    second = collections.Counter(b for _, b in pairs)
    expected = sum(first[label] * second[label] for label in set(first) | set(second))
    expected /= total * total
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1 - expected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("first")
    parser.add_argument("second")
    parser.add_argument("--show", type=int, default=10,
                        help="how many disagreements to print")
    args = parser.parse_args()

    a, b = load(args.first), load(args.second)
    shared = sorted(set(a) & set(b))
    print(f"{len(a)} labels in the first pass, {len(b)} in the second, "
          f"{len(shared)} tickets labelled by both\n")
    if not shared:
        raise SystemExit("no overlap - there is nothing to compare")

    print(f"{'field':24}{'agree':>7}{'of':>5}{'rate':>8}{'kappa':>8}")
    for field in ("category", "priority", "next_step"):
        pairs = [(str(a[t].get(field)), str(b[t].get(field))) for t in shared]
        same = sum(1 for x, y in pairs if x == y)
        kappa = cohen_kappa(pairs)
        print(f"  {field:22}{same:>7}{len(pairs):>5}{same / len(pairs):>8.0%}"
              f"{kappa:>8.2f}")

    # Secondary categories are a set, so exact match is the wrong test: report
    # the overlap instead, which is what a retrieval-style metric would use.
    jaccards = []
    for ticket in shared:
        first = set(a[ticket].get("secondary_categories") or [])
        second = set(b[ticket].get("secondary_categories") or [])
        union = first | second
        jaccards.append(1.0 if not union else len(first & second) / len(union))
    print(f"  {'secondary (Jaccard)':22}{'':>7}{len(jaccards):>5}"
          f"{sum(jaccards) / len(jaccards):>8.0%}")

    gaps = [abs(float(a[t].get("confidence", 0)) - float(b[t].get("confidence", 0)))
            for t in shared]
    print(f"  {'confidence (mean gap)':22}{'':>7}{len(gaps):>5}"
          f"{sum(gaps) / len(gaps):>8.2f}")

    disagreements = [t for t in shared
                     if a[t].get("category") != b[t].get("category")
                     or a[t].get("priority") != b[t].get("priority")
                     or a[t].get("next_step") != b[t].get("next_step")]
    print(f"\n{len(disagreements)} of {len(shared)} tickets differ on at least "
          f"one field. These are the rubric's real boundaries, and they belong "
          f"in the report:")
    for ticket in disagreements[:args.show]:
        print(f"\n  {ticket}")
        for field in ("category", "priority", "next_step"):
            first, second = a[ticket].get(field), b[ticket].get(field)
            mark = " " if first == second else "*"
            print(f"    {mark} {field:12} {str(first):24} | {second}")
        print(f"      A: {a[ticket].get('rationale', '')[:110]}")
        print(f"      B: {b[ticket].get('rationale', '')[:110]}")


if __name__ == "__main__":
    main()
