"""Remove one block of the prompt at a time and see whether it still pays.

    python eval/ablation.py --base v5

v5 is 7,000 characters, grown one block per version from observed failures. Two
things follow that a version-to-version table cannot answer: a block that helped
at v2 may be carried by a later block instead, and an overloaded prompt is an
antipattern in its own right - past some length the model starts ignoring parts
of it. The only way to find out which blocks still earn their place is to take
each one out and re-measure.

The variants are built in memory. They are not prompt versions - nothing here is
meant to ship - so they get no .txt file; the hash of each rendered variant is
recorded instead, which is what makes the numbers reproducible.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "eval"))
from app.config import load                                           # noqa: E402
from app.llm import classify, render                                  # noqa: E402
from score import score                                               # noqa: E402

# (name, first line of the block, last line of the block). Each block is one
# version's contribution, except that v3 added two at once - the escalation
# triggers and the routing list - and they are separable, so they are separated.
BLOCKS = [
    ("precedence",
     "The primary category is the CAUSE",
     "for the charges to stop."),
    ("priority_rules",
     "Priority and next_step are separate decisions.",
     "large the sum was."),
    ("escalation_triggers",
     "Escalate to a human when the ticket states",
     "those go to the specific step."),
    ("routing_criteria",
     "When no escalation trigger is present",
     "-> acknowledge_and_close"),
]


def without(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i) + len(end)
    # Take the trailing blank line with the block, or the removal leaves a hole.
    while j < len(text) and text[j] in "\n":
        j += 1
    return text[:i] + text[j:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="v5")
    parser.add_argument("--set", default="dev", choices=["dev", "golden"])
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    settings = load(args.base)
    base = settings.prompt
    full = render(base)

    with open(os.path.join(ROOT, "data", "tickets", f"{args.set}.json"),
              encoding="utf-8") as handle:
        tickets = json.load(handle)

    variants = [("full", full)]
    for name, start, end in BLOCKS:
        variants.append((f"no_{name}", without(full, start, end)))

    report = []
    for name, text in variants:
        prompt = base.model_copy(update={"text_override": text})
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(
                lambda ticket: classify(ticket, settings, prompt=prompt), tickets))
        run = {
            "set": args.set,
            "prompt_version": f"{args.base}:{name}",
            "model": prompt.model,
            "tickets": len(results),
            "cost_usd": sum(r.cost_usd for r in results),
            "results": [dict(asdict(r),
                             triage=r.triage.model_dump(mode="json") if r.triage else None)
                        for r in results],
        }
        summary = score(run)["summary"]
        summary["chars"] = len(text)
        summary["prompt_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        report.append(summary)
        print(f"{name:24} {summary['category_accuracy']:5.0%} cat  "
              f"{summary['priority_accuracy']:5.0%} pri  "
              f"{summary['next_step_accuracy']:5.0%} step  "
              f"{summary['all_three_accuracy']:5.0%} all3  "
              f"${summary['cost_per_10k']:6.2f}/10k  {len(text):,} chars")

    base_row = report[0]
    lines = [f"# Ablation of {args.base} on {args.set}", "",
             "Each row is the prompt with ONE block removed. A block that costs "
             "nothing to remove is not doing the work its version claimed.", "",
             "| variant | category | priority | next_step | all three | $/10k | chars |",
             "|---|---|---|---|---|---|---|"]
    for row in report:
        delta = "" if row is base_row else \
            f" ({row['all_three_accuracy'] - base_row['all_three_accuracy']:+.0%})"
        lines.append(
            f"| {row['prompt_version'].split(':')[1]} "
            f"| {row['category_accuracy']:.0%} | {row['priority_accuracy']:.0%} "
            f"| {row['next_step_accuracy']:.0%} | {row['all_three_accuracy']:.0%}{delta} "
            f"| ${row['cost_per_10k']:.2f} | {row['chars']:,} |")
    lines += ["", "A negative delta means removing the block made it worse, so "
                  "the block earns its place.", ""]

    out = os.path.join(ROOT, "eval", "results", f"ablation__{args.set}__{args.base}")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(f"{out}.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    with open(f"{out}.md", "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    total = sum(r["cost_usd"] for r in report)
    print(f"\ntotal ${total:.4f}  ->  eval/results/ablation__{args.set}__{args.base}.md")


if __name__ == "__main__":
    main()
