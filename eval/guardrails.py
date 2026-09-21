"""Run the synthetic edge cases and check behaviour, not accuracy.

    python eval/guardrails.py                    # the prompt in config
    python eval/guardrails.py --prompt v6 --model anthropic/claude-haiku-4.5

WHY THESE ARE SCORED DIFFERENTLY
    The real sets measure how often the model agrees with a human label. These
    fifteen measure whether it ever does something unacceptable, which is not the
    same question and must not share a number with it. A synthetic case can only
    ever fail here: there is no category to get right, so adding easy rows cannot
    lift any score. That is deliberate - hand-written cases scored like the
    golden set would be a way to grade your own homework.

    Lecture 19 calls this the adversarial / red-team part of an eval pipeline and
    keeps it beside the golden dataset rather than inside it.

WHAT A CHECK CAN ASSERT
    next_step / priority        the answer must be one of these
    must_not_next_step          these are unacceptable whatever the category
    must_not_priority           same, for priority
    must_not_contain            this string must not appear in evidence or
                                rationale - used for PII and for injected text
    schema_valid                a usable object came back at all
    max_confidence              the model must NOT be confident here
    min_secondary               a multi-topic ticket must admit more than one
    evidence_in_text            the quote must be copied, not composed
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.config import load                                           # noqa: E402
from app.llm import classify                                          # noqa: E402

WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    return WS.sub(" ", text).strip().lower()


def check(case: dict, result) -> list[str]:
    """Returns the failures. An empty list is a pass."""
    expect = case["expect"]
    failures = []

    if not result.ok:
        if expect.get("schema_valid"):
            return [f"no valid output at all: {result.error}"]
        return [f"no valid output: {result.error}"]

    triage = result.triage
    step, priority = triage.next_step.value, triage.priority.value
    haystack = normalise(triage.evidence + " " + triage.rationale)

    if expect.get("next_step") and step not in expect["next_step"]:
        failures.append(f"next_step {step}, expected one of {expect['next_step']}")
    if expect.get("priority") and priority not in expect["priority"]:
        failures.append(f"priority {priority}, expected one of {expect['priority']}")
    if step in expect.get("must_not_next_step", []):
        failures.append(f"next_step {step} is not acceptable here")
    if priority in expect.get("must_not_priority", []):
        failures.append(f"priority {priority} is not acceptable here")
    for forbidden in expect.get("must_not_contain", []):
        if normalise(forbidden) in haystack:
            failures.append(f"output repeats {forbidden!r}")
    if "max_confidence" in expect and triage.confidence > expect["max_confidence"]:
        failures.append(f"confidence {triage.confidence} above "
                        f"{expect['max_confidence']} on a ticket this thin")
    if "min_secondary" in expect and len(triage.secondary_categories) < expect["min_secondary"]:
        failures.append(f"{len(triage.secondary_categories)} secondary categories, "
                        f"expected at least {expect['min_secondary']}")
    if expect.get("evidence_in_text") and normalise(triage.evidence) not in normalise(case["text"]):
        failures.append("evidence is not a verbatim span of the ticket")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    settings = load(args.prompt)
    prompt = settings.prompt
    model = args.model or prompt.model

    with open(os.path.join(ROOT, "data", "tickets", "synthetic.json"),
              encoding="utf-8") as handle:
        cases = json.load(handle)

    print(f"{len(cases)} edge cases | prompt {prompt.version} | model {model}\n")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(
            lambda case: classify(case, settings, model=model, prompt=prompt),
            cases))

    report, failed = [], 0
    for case, result in zip(cases, results):
        failures = check(case, result)
        failed += bool(failures)
        answer = (f"{result.triage.category.value} P{result.triage.priority.value} "
                  f"{result.triage.next_step.value} conf {result.triage.confidence:.2f}"
                  if result.ok else f"ERROR {result.error}")
        print(f"[{'FAIL' if failures else 'pass'}] {case['ticket_id']:26} {answer}")
        for failure in failures:
            print(f"        - {failure}")
        report.append({"ticket_id": case["ticket_id"], "why": case["why"],
                       "passed": not failures, "failures": failures,
                       "answer": answer,
                       "triage": result.triage.model_dump(mode="json") if result.ok else None,
                       "cost_usd": result.cost_usd})

    cost = sum(r.cost_usd for r in results)
    print(f"\n{len(cases) - failed}/{len(cases)} passed   ${cost:.4f}")

    out = os.path.join(ROOT, "eval", "results",
                       f"guardrails__{prompt.version}__{model.replace('/', '-')}")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(f"{out}.json", "w", encoding="utf-8") as handle:
        json.dump({"prompt_version": prompt.version, "model": model,
                   "passed": len(cases) - failed, "cases": len(cases),
                   "cost_usd": cost, "results": report},
                  handle, ensure_ascii=False, indent=2)

    lines = [f"# Edge cases: {prompt.version} / {model}", "",
             f"**{len(cases) - failed} of {len(cases)} passed.** These are "
             "behaviour checks, not accuracy: a case can only fail, so nothing "
             "here can raise a score reported elsewhere.", "",
             "| case | what it probes | answer | verdict |", "|---|---|---|---|"]
    for row in report:
        verdict = "pass" if row["passed"] else "**FAIL** - " + "; ".join(row["failures"])
        lines.append(f"| {row['ticket_id']} | {row['why'][:120]} "
                     f"| {row['answer']} | {verdict} |")
    lines.append("")
    with open(f"{out}.md", "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print(f"wrote {os.path.relpath(out, ROOT)}.md and .json")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
