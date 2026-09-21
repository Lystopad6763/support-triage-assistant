"""One table of every scored run, so versions can be compared later.

    python eval/ledger.py                 # rebuild and print
    python eval/ledger.py --set dev       # one set only

DERIVED, NOT APPENDED
    The ledger is rebuilt from eval/results/*.json every time. An append-only
    log drifts from the runs behind it the first time someone deletes a bad run
    or rescores after fixing a label - and rescoring is exactly what happened
    here, when four labels turned out to be wrong and every earlier number moved.
    Rebuilding means the table can never claim a number that no run file holds.

WHAT A ROW IS
    One scored run: set, prompt version, the hash of the RENDERED prompt, model,
    seed, the metrics, and when it ran. The hash matters more than the version
    name: two runs both called v5 with different hashes are two different prompts
    and must not be averaged.

WHAT THE SUMMARY IS
    Repeats of the same cell collapsed into mean +- spread. temperature 0 is not
    deterministic here - six runs of v5 on dev spread 68-80% on category - so a
    single number without its spread invites a conclusion the data does not
    support.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "eval", "results")
# Reports written by other tools have their own shape and their own files.
# "_smoke" is how scripts/triage.py names a partial run. It is evidence of a
# pipeline working, never of a prompt performing, and it must not reach a mean.
SKIP = ("ablation__", "benchmark__", "label_audit", "ledger", "_smoke")

COLUMNS = ("set", "prompt_version", "prompt_sha256", "model", "seed", "tickets",
           "category_accuracy", "macro_f1", "priority_accuracy",
           "next_step_accuracy", "all_three_accuracy", "evidence_verbatim_rate",
           "escalation_precision", "escalation_recall", "hard_failures",
           "repaired", "cost_per_10k", "started_at", "run")


def rows() -> list[dict]:
    out = []
    for path in sorted(glob.glob(os.path.join(RESULTS, "*.json"))):
        name = os.path.basename(path)
        if any(name.startswith(prefix) or prefix in name for prefix in SKIP):
            continue
        with open(path, encoding="utf-8") as handle:
            report = json.load(handle)
        if not isinstance(report, dict) or "summary" not in report:
            continue
        s = report["summary"]
        esc = s.get("escalation") or {}
        out.append({
            "set": s["set"],
            "prompt_version": s["prompt_version"],
            "prompt_sha256": s.get("prompt_sha256") or "-",
            "model": s["model"],
            "seed": s.get("seed") if s.get("seed") is not None else "-",
            "tickets": s["tickets"],
            "category_accuracy": s["category_accuracy"],
            # None, not 0.0: a run scored before this metric existed has no
            # value, and averaging a zero in would quietly understate the cell.
            "macro_f1": s.get("macro_f1"),
            "priority_accuracy": s["priority_accuracy"],
            "next_step_accuracy": s["next_step_accuracy"],
            "all_three_accuracy": s["all_three_accuracy"],
            "evidence_verbatim_rate": s["evidence_verbatim_rate"],
            "escalation_precision": esc.get("precision", 0.0),
            "escalation_recall": esc.get("recall", 0.0),
            "hard_failures": s["hard_failures"],
            "repaired": s.get("repaired", 0),
            "cost_per_10k": s["cost_per_10k"],
            # Falls back to the file's own mtime for runs made before
            # started_at was recorded, which is most of the early ones.
            "started_at": s.get("started_at") or "(file %s)" % (
                __import__("datetime").datetime.fromtimestamp(
                    os.path.getmtime(path)).isoformat(timespec="minutes")),
            "run": os.path.splitext(name)[0],
        })
    return out


def summarise(data: list[dict]) -> list[dict]:
    cells: dict[tuple, list[dict]] = {}
    for row in data:
        cells.setdefault((row["set"], row["prompt_version"], row["model"]), []).append(row)
    out = []
    for (dataset, version, model), group in sorted(cells.items()):
        entry = {"set": dataset, "prompt_version": version, "model": model,
                 "runs": len(group),
                 "hashes": len({g["prompt_sha256"] for g in group})}
        for field in ("category_accuracy", "macro_f1", "priority_accuracy",
                      "next_step_accuracy", "all_three_accuracy", "cost_per_10k"):
            values = [g[field] for g in group if g[field] is not None]
            entry[field] = st.mean(values) if values else None
            entry[field + "_sd"] = st.stdev(values) if len(values) > 1 else 0.0
            entry[field + "_n"] = len(values)
        out.append(entry)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", default=None, choices=["dev", "golden"])
    args = parser.parse_args()

    data = rows()
    if args.set:
        data = [r for r in data if r["set"] == args.set]
    if not data:
        print("no scored runs in eval/results - run eval/score.py first")
        return

    with open(os.path.join(RESULTS, "ledger.csv"), "w", encoding="utf-8",
              newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(data)

    summary = summarise(data)
    lines = ["# Run ledger", "",
             "Rebuilt from eval/results/*.json by eval/ledger.py - never typed, "
             "and never appended to, so it cannot outlive the runs it reports.",
             "",
             "## Per prompt version (repeats collapsed)", "",
             "| set | prompt | model | runs | category | macro F1 | priority | "
             "next_step | all three | $/10k |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for row in summary:
        warn = " !" if row["hashes"] > 1 else ""
        lines.append(
            f"| {row['set']} | {row['prompt_version']}{warn} | {row['model']} "
            f"| {row['runs']} "
            f"| {row['category_accuracy']:.0%} +-{row['category_accuracy_sd']:.0%} "
            f"| {'-' if row['macro_f1'] is None else format(row['macro_f1'], '.2f')} "
            f"| {row['priority_accuracy']:.0%} "
            f"| {row['next_step_accuracy']:.0%} "
            f"| {row['all_three_accuracy']:.0%} "
            f"| ${row['cost_per_10k']:.2f} |")
    if any(r["hashes"] > 1 for r in summary):
        lines += ["", "! = runs under this version name used different rendered "
                      "prompts, so their numbers are not comparable and the mean "
                      "is meaningless. Check prompt_sha256 in ledger.csv."]
    lines += ["", "## Every run", "",
              "| set | prompt | hash | model | seed | category | macro F1 | "
              "all three | evidence | fails | $/10k | when |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in sorted(data, key=lambda r: (r["set"], r["prompt_version"],
                                           r["model"], str(r["started_at"]))):
        lines.append(
            f"| {row['set']} | {row['prompt_version']} | `{row['prompt_sha256']}` "
            f"| {row['model']} | {row['seed']} "
            f"| {row['category_accuracy']:.0%} "
            f"| {'-' if row['macro_f1'] is None else format(row['macro_f1'], '.2f')} "
            f"| {row['all_three_accuracy']:.0%} "
            f"| {row['evidence_verbatim_rate']:.0%} | {row['hard_failures']} "
            f"| ${row['cost_per_10k']:.2f} | {row['started_at']} |")
    lines.append("")

    with open(os.path.join(RESULTS, "ledger.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    print(f"{len(data)} runs, {len(summary)} cells")
    print(f"{'set':7} {'prompt':7} {'model':22} {'n':>2} {'cat':>10} "
          f"{'F1':>5} {'all3':>6} {'$/10k':>7}")
    for row in summary:
        mark = "!" if row["hashes"] > 1 else " "
        print(f"{row['set']:7} {row['prompt_version']:6}{mark} {row['model']:22} "
              f"{row['runs']:2} {row['category_accuracy']:6.0%} "
              f"+-{row['category_accuracy_sd']:3.0%} "
              f"{'    -' if row['macro_f1'] is None else format(row['macro_f1'], '5.2f')} "
              f"{row['all_three_accuracy']:6.0%} {row['cost_per_10k']:7.2f}")
    print("\nwrote eval/results/ledger.md and ledger.csv")


if __name__ == "__main__":
    main()
