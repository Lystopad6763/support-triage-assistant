"""Merge labels into a ticket set, validating every value against the taxonomy.

    python scripts/apply_labels.py data/tickets/golden.json labels/golden/*.json

WHY A SCRIPT AND NOT AN EDIT
    Labels get revised - that is the point of having a second reader - and a
    label edited by hand in a 160 KB JSON file is a typo waiting to become a
    silent evaluation error. Here a category that does not exist stops the run
    and names the ticket it came from.

WHAT IT REFUSES TO DO
    Overwrite an existing label unless --replace is given, and write anything
    at all if a single value fails validation. A half-labelled file that looks
    finished is worse than one that is obviously unfinished.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from app.taxonomy import Category, NextStep, Priority                 # noqa: E402
from criteria import kb_for_category                                  # noqa: E402

REQUIRED = {"category", "secondary_categories", "priority", "next_step",
            "rationale", "confidence"}
# Written by this script from the category, never supplied in a label file: a
# hand-written value here could contradict the category it describes.
DERIVED = {"kb_covered", "kb_articles"}


def validate(ticket_id: str, label: dict) -> list[str]:
    problems = []
    missing = REQUIRED - set(label)
    if missing:
        problems.append(f"{ticket_id}: missing {sorted(missing)}")
    extra = set(label) - REQUIRED - DERIVED
    if extra:
        problems.append(f"{ticket_id}: unexpected fields {sorted(extra)}")

    category = label.get("category")
    if category not in {c.value for c in Category}:
        problems.append(f"{ticket_id}: category {category!r} is not in the taxonomy")
    if label.get("priority") not in {p.value for p in Priority}:
        problems.append(f"{ticket_id}: priority {label.get('priority')!r} is not 1, 2 or 3")
    if label.get("next_step") not in {s.value for s in NextStep}:
        problems.append(f"{ticket_id}: next_step {label.get('next_step')!r} is not in the taxonomy")

    secondary = label.get("secondary_categories") or []
    if not isinstance(secondary, list):
        problems.append(f"{ticket_id}: secondary_categories must be a list")
    else:
        for item in secondary:
            if item not in {c.value for c in Category}:
                problems.append(f"{ticket_id}: secondary {item!r} is not in the taxonomy")
        if category in secondary:
            problems.append(f"{ticket_id}: {category!r} is both primary and secondary")
        if len(set(secondary)) != len(secondary):
            problems.append(f"{ticket_id}: secondary_categories repeats itself")

    confidence = label.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
        problems.append(f"{ticket_id}: confidence {confidence!r} is not between 0 and 1")
    if not str(label.get("rationale", "")).strip():
        problems.append(f"{ticket_id}: rationale is empty")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("dataset", help="data/tickets/golden.json")
    parser.add_argument("labels", nargs="+", help="one or more label JSON files")
    parser.add_argument("--replace", action="store_true",
                        help="allow overwriting labels that are already there")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = json.load(open(args.dataset, encoding="utf-8"))
    by_id = {row["ticket_id"]: row for row in rows}

    labels: dict[str, dict] = {}
    for pattern in args.labels:
        for path in sorted(glob.glob(pattern)) or [pattern]:
            batch = json.load(open(path, encoding="utf-8"))
            overlap = set(batch) & set(labels)
            if overlap:
                raise SystemExit(f"{path} relabels tickets another file already "
                                 f"covered: {sorted(overlap)[:5]}")
            labels.update(batch)
            print(f"  {os.path.basename(path):<28} {len(batch):4d} labels")

    problems = []
    for ticket_id, label in labels.items():
        if ticket_id not in by_id:
            problems.append(f"{ticket_id}: not in {os.path.basename(args.dataset)}")
            continue
        if by_id[ticket_id].get("label") is not None and not args.replace:
            problems.append(f"{ticket_id}: already labelled (use --replace)")
        problems += validate(ticket_id, label)

    unlabelled = [r["ticket_id"] for r in rows if r["ticket_id"] not in labels
                  and r.get("label") is None]
    if problems:
        print(f"\n{len(problems)} problems, nothing written:")
        for problem in problems[:40]:
            print(f"  {problem}")
        raise SystemExit(1)

    for ticket_id, label in labels.items():
        # Derived here rather than written by hand, so it cannot disagree with
        # the category it is derived from. This is the field that answers "does
        # our knowledge base answer this ticket?" with yes or no - the draw-time
        # guess in `selection` has a third value because the probes cannot name
        # the subject of every row, and once a label exists that excuse is gone.
        # The PRIMARY category decides it: a dispute that also mentions a refund
        # is not answered by the refund article, it is half-answered by it.
        articles = kb_for_category(label["category"])
        label["kb_covered"] = bool(articles)
        label["kb_articles"] = articles
        by_id[ticket_id]["label"] = label

    labelled = sum(1 for r in rows if r.get("label") is not None)
    print(f"\n{labelled}/{len(rows)} rows labelled"
          + (f", {len(unlabelled)} still empty" if unlabelled else ", none left"))
    if args.dry_run:
        print("dry run - nothing written")
        return
    with open(args.dataset, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"written: {args.dataset}")


if __name__ == "__main__":
    main()
