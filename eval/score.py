"""Score a run against the labelled set and write the tables the report needs.

    python eval/score.py data/runs/dev__v1__openai-gpt-5-mini.json

Writes eval/results/<run>.md and .json, and prints the same numbers. Generated,
never typed by hand: a table typed into a README drifts from the run behind it
and then argues with it in public.

WHY NOT ONLY ACCURACY
    The evaluation lecture calls accuracy-as-the-only-metric an antipattern: it
    does not separate "right for the right reason" from "right by accident", and
    on skewed classes it hides everything. Two thirds of both sets are billing,
    so a model that answers cancellation_failed to everything scores well and is
    useless. Hence per-class precision/recall/F1 and a macro F1 that weights a
    class with 2 rows the same as one with 20.

    The monitoring lecture adds the per-bucket cut: an average hides degradation
    that a bucket shows immediately. A quarter of both sets is not English, so
    accuracy is also reported by language, by aggressive tone, by multi-topic and
    by whether the knowledge base covers the ticket at all.

WHAT COUNTS AS CORRECT
    category, priority, next_step   exact match against the label
    secondary_categories            Jaccard - a set, so partial credit is honest
    evidence                        must appear verbatim in the ticket text. A
                                    quote the model composed is not evidence,
                                    and it is the one field a human reviewer
                                    checks first, so it is scored.

    next_step is reported but is NOT the headline number. Two of its values can
    both be defensible for one ticket (ask_purchase_rail vs escalate_to_human on
    a ticket that names no store), which is why the two human passes agreed on
    80% of it against 100% on priority. Category is the headline.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.taxonomy import Category                                     # noqa: E402

WS = re.compile(r"\s+")


# Curly quote, curly apostrophe, en and em dash, non-breaking space, ellipsis.
# A ticket typed on a phone is full of them; a model quoting it back often is not.
TYPOGRAPHIC = {
    "\u2018": "'", "\u2019": "'", "\u02bc": "'", "\u00b4": "'", "\u0060": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-",
    "\u00a0": " ", "\u2026": "...",
}


def normalise(text: str) -> str:
    """Fold whitespace, case and typographic punctuation.

    The last one is not cosmetic. `evidence_verbatim` asks whether the quote is
    IN the ticket, and a model that reproduces an apostrophe as ' where the
    writer typed the curly one has still quoted the ticket. Without this fold
    the metric scored claude-haiku-4.5 at 78% where it belongs at 93%, while
    leaving the other nine models within a point - it was measuring which model
    normalises punctuation, not which one invents evidence.
    """
    for fancy, plain in TYPOGRAPHIC.items():
        text = text.replace(fancy, plain)
    return WS.sub(" ", text).strip().lower()


def jaccard(left: list[str], right: list[str]) -> float:
    a, b = set(left), set(right)
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def per_class(rows: list[dict]) -> dict:
    """Precision, recall and F1 per category, and the macro average.

    Macro, not weighted: a class with two rows in the set is still a class an
    agent has to route correctly, and weighting by support would let the two big
    billing classes speak for the whole taxonomy.
    """
    labels = sorted({r["expected"]["category"] for r in rows}
                    | {r["actual"]["category"] for r in rows})
    out = {}
    for label in labels:
        tp = sum(1 for r in rows if r["expected"]["category"] == label
                 and r["actual"]["category"] == label)
        fp = sum(1 for r in rows if r["expected"]["category"] != label
                 and r["actual"]["category"] == label)
        fn = sum(1 for r in rows if r["expected"]["category"] == label
                 and r["actual"]["category"] != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out[label] = {"support": tp + fn, "predicted": tp + fp,
                      "precision": precision, "recall": recall, "f1": f1}
    # Both averages are computed before any underscore key is added to `out`,
    # or the float would end up in the list of classes.
    scored = [v for v in out.values() if v["support"]]
    core = [v for v in scored if v["support"] >= 3]
    out["_macro_f1"] = sum(v["f1"] for v in scored) / len(scored) if scored else 0.0
    # F1 is one number over two failures and cannot say which one happened. A
    # class at F1 0.73 with precision 0.95 and recall 0.59 is a model that is
    # right when it commits and commits too rarely; the same 0.73 with the halves
    # swapped is a model that grabs the class from its neighbours. The first
    # calls for a wider definition, the second for a sharper exclusion - opposite
    # prompt edits, indistinguishable from F1 alone.
    out["_macro_precision"] = (sum(v["precision"] for v in scored) / len(scored)
                               if scored else 0.0)
    out["_macro_recall"] = (sum(v["recall"] for v in scored) / len(scored)
                            if scored else 0.0)
    # Macro over the classes with enough rows to mean anything. F1 on a class
    # with one row is 0 or 1 - a coin flip - and averaging those coins in with
    # the reliable classes is why macro_f1 itself swings 0.65-0.81 across
    # identical runs. The threshold is 3, which on dev keeps the four billing
    # classes holding 43 of the 50 rows.
    out["_macro_f1_core"] = sum(v["f1"] for v in core) / len(core) if core else 0.0
    out["_macro_precision_core"] = (sum(v["precision"] for v in core) / len(core)
                                    if core else 0.0)
    out["_macro_recall_core"] = (sum(v["recall"] for v in core) / len(core)
                                 if core else 0.0)
    out["_core_classes"] = len(core)
    return out


def buckets(rows: list[dict], tickets: dict[str, dict]) -> dict:
    """Accuracy by slice. An average over 50 rows can hold at 80% while every
    Korean ticket is wrong, and the only way to see that is to cut."""
    def language(row):
        flags = tickets[row["ticket_id"]]["selection"]["flags"]
        if flags.get("non_latin_script"):
            return "non-latin script"
        return "non-english latin" if flags.get("non_english") else "english"

    cuts = {
        "language": language,
        "tone": lambda r: ("aggressive" if tickets[r["ticket_id"]]["selection"]
                           ["flags"].get("aggressive") else "plain"),
        "topics": lambda r: ("multi-topic" if tickets[r["ticket_id"]]["selection"]
                             ["flags"].get("multi_topic") else "single topic"),
        "kb": lambda r: ("kb has an answer"
                         if tickets[r["ticket_id"]]["label"].get("kb_covered")
                         else "not in the kb"),
    }
    out = {}
    for name, key in cuts.items():
        groups = {}
        for row in rows:
            groups.setdefault(key(row), []).append(row)
        out[name] = {
            value: {"n": len(group),
                    "category": sum(r["category_ok"] for r in group) / len(group),
                    "all_three": sum(r["category_ok"] and r["priority_ok"]
                                     and r["next_step_ok"] for r in group) / len(group)}
            for value, group in sorted(groups.items())
        }
    return out


def percentile(values, p: float) -> int:
    """Nearest-rank percentile, and correct at small n.

    The expression this replaces - sorted[int(len * 0.95) - 1] - was wrong twice
    over. At n=2 it returns the SMALLEST value, and a two-ticket run really did
    print "median 8133ms p95 5754ms", a p95 below its own median. At n=50 it
    returns the 47th of 50 where p95 is the 48th. Both errors point the same way:
    they flatter the tail, which is the one number a tail metric must not do.
    """
    if not values:
        return 0
    ordered = sorted(values)
    rank = max(1, math.ceil(p * len(ordered)))
    return ordered[min(len(ordered) - 1, rank - 1)]


def escalation(rows: list[dict]) -> dict:
    """Escalation is the decision with a real price on both sides: a missed one
    costs a customer, a false one costs an agent's hour. Accuracy over nine
    next_step values cannot show which way the errors go."""
    step = "escalate_to_human"
    tp = sum(1 for r in rows if r["expected"]["next_step"] == step == r["actual"]["next_step"])
    fp = sum(1 for r in rows if r["expected"]["next_step"] != step
             and r["actual"]["next_step"] == step)
    fn = sum(1 for r in rows if r["expected"]["next_step"] == step
             and r["actual"]["next_step"] != step)
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall": tp / (tp + fn) if tp + fn else 0.0}


def load_tickets(name: str) -> dict[str, dict]:
    path = os.path.join(ROOT, "data", "tickets", f"{name}.json")
    with open(path, encoding="utf-8") as handle:
        return {row["ticket_id"]: row for row in json.load(handle)}


def score(run: dict) -> dict:
    tickets = load_tickets(run["set"])
    rows, failures = [], []

    for result in run["results"]:
        ticket = tickets[result["ticket_id"]]
        expected = ticket["label"]
        if not result["triage"]:
            failures.append({"ticket_id": result["ticket_id"],
                             "error": result["error"],
                             "attempts": result["attempts"]})
            continue
        actual = result["triage"]
        rows.append({
            "ticket_id": result["ticket_id"],
            "text": ticket["text"],
            "expected": expected,
            "actual": actual,
            "category_ok": actual["category"] == expected["category"],
            "priority_ok": actual["priority"] == expected["priority"],
            "next_step_ok": actual["next_step"] == expected["next_step"],
            "secondary_jaccard": jaccard(actual["secondary_categories"],
                                         expected["secondary_categories"]),
            # Verbatim means present in the text, not merely plausible.
            "evidence_verbatim": normalise(actual["evidence"]) in normalise(ticket["text"]),
            "confidence": actual["confidence"],
            "latency_ms": result["latency_ms"],
            "repaired": result["repaired"],
        })

    scored = len(rows) or 1
    summary = {
        "set": run["set"],
        "prompt_version": run["prompt_version"],
        "model": run["model"],
        "started_at": run.get("started_at"),
        "prompt_sha256": run.get("prompt_sha256"),
        "seed": run.get("seed"),
        "temperature": run.get("temperature"),
        "tickets": run["tickets"],
        "scored": len(rows),
        "hard_failures": len(failures),
        "category_accuracy": sum(r["category_ok"] for r in rows) / scored,
        "priority_accuracy": sum(r["priority_ok"] for r in rows) / scored,
        "next_step_accuracy": sum(r["next_step_ok"] for r in rows) / scored,
        "all_three_accuracy": sum(r["category_ok"] and r["priority_ok"]
                                  and r["next_step_ok"] for r in rows) / scored,
        "secondary_jaccard": sum(r["secondary_jaccard"] for r in rows) / scored,
        "evidence_verbatim_rate": sum(r["evidence_verbatim"] for r in rows) / scored,
        "repaired": sum(r["repaired"] for r in rows),
        "cost_usd": run["cost_usd"],
        "cost_per_ticket": run["cost_usd"] / (run["tickets"] or 1),
        "cost_per_10k": run["cost_usd"] / (run["tickets"] or 1) * 10_000,
    }
    # Confidence is only useful if it is lower when the model is wrong. If these
    # two numbers are equal, confidence cannot be used as a routing signal and
    # the gate has to rely on something else.
    right = [r["confidence"] for r in rows if r["category_ok"]]
    wrong = [r["confidence"] for r in rows if not r["category_ok"]]
    summary["confidence_when_right"] = sum(right) / len(right) if right else None
    summary["confidence_when_wrong"] = sum(wrong) / len(wrong) if wrong else None

    classes = per_class(rows) if rows else {"_macro_f1": 0.0, "_macro_f1_core": 0.0,
                                            "_core_classes": 0}
    summary["macro_f1"] = classes["_macro_f1"]
    summary["macro_precision"] = classes.get("_macro_precision")
    summary["macro_recall"] = classes.get("_macro_recall")
    summary["macro_f1_core"] = classes.get("_macro_f1_core")
    summary["macro_precision_core"] = classes.get("_macro_precision_core")
    summary["macro_recall_core"] = classes.get("_macro_recall_core")
    summary["core_classes"] = classes.get("_core_classes")
    summary["escalation"] = escalation(rows) if rows else {}

    confusion = Counter((r["expected"]["category"], r["actual"]["category"])
                        for r in rows if not r["category_ok"])
    return {"summary": summary, "rows": rows, "failures": failures,
            "per_class": classes,
            "buckets": buckets(rows, tickets) if rows else {},
            "confusion": [{"expected": e, "actual": a, "count": n}
                          for (e, a), n in confusion.most_common()]}


def markdown(report: dict) -> str:
    s = report["summary"]
    out = [
        f"# {s['set']} / prompt {s['prompt_version']} / {s['model']}",
        "",
        f"| metric | value |",
        f"|---|---|",
        f"| tickets | {s['tickets']} |",
        f"| scored (returned valid output) | {s['scored']} |",
        f"| hard failures | {s['hard_failures']} |",
        f"| category accuracy | **{s['category_accuracy']:.0%}** |",
        f"| macro F1 over categories | **{s['macro_f1']:.2f}** |",
        f"| macro precision / recall over categories | "
        f"{s['macro_precision']:.2f} / {s['macro_recall']:.2f} |",
        f"| macro precision / recall over classes with 3+ rows | "
        f"{s['macro_precision_core']:.2f} / {s['macro_recall_core']:.2f} |",
        f"| macro F1 over classes with 3+ rows | **{s['macro_f1_core']:.2f}** "
        f"({s['core_classes']} classes) |",
        f"| priority accuracy | {s['priority_accuracy']:.0%} |",
        f"| next_step accuracy | {s['next_step_accuracy']:.0%} |",
        f"| all three correct | {s['all_three_accuracy']:.0%} |",
        f"| secondary categories (Jaccard) | {s['secondary_jaccard']:.0%} |",
        f"| evidence verbatim | {s['evidence_verbatim_rate']:.0%} |",
        f"| repaired after invalid JSON | {s['repaired']} |",
        f"| confidence when right / wrong | "
        f"{_fmt(s['confidence_when_right'])} / {_fmt(s['confidence_when_wrong'])} |",
        f"| cost | ${s['cost_usd']:.5f} = ${s['cost_per_ticket']:.5f}/ticket "
        f"= ${s['cost_per_10k']:.2f}/10k |",
        "",
    ]
    esc = s.get("escalation") or {}
    if esc:
        out += [f"| escalation precision / recall | {esc['precision']:.0%} / "
                f"{esc['recall']:.0%} (missed {esc['fn']}, spurious {esc['fp']}) |", ""]

    classes = report.get("per_class") or {}
    if classes:
        out += ["## Per category", "",
                "| category | in set | predicted | precision | recall | F1 |",
                "|---|---|---|---|---|---|"]
        for name, row in sorted(classes.items(),
                                key=lambda kv: -kv[1]["support"]
                                if isinstance(kv[1], dict) else 0):
            if not isinstance(row, dict):
                continue
            thin = " (too few rows to read)" if 0 < row["support"] < 3 else ""
            out.append(f"| {name} | {row['support']}{thin} | {row['predicted']} "
                       f"| {row['precision']:.0%} | {row['recall']:.0%} "
                       f"| {row['f1']:.2f} |")
        out.append("")

    if report.get("buckets"):
        out += ["## By slice", "",
                "An average over 50 rows can sit at 80% while a whole language "
                "is wrong.", "",
                "| cut | slice | n | category | all three |",
                "|---|---|---|---|---|"]
        for cut, groups in report["buckets"].items():
            for value, row in groups.items():
                out.append(f"| {cut} | {value} | {row['n']} "
                           f"| {row['category']:.0%} | {row['all_three']:.0%} |")
        out.append("")

    if report["confusion"]:
        out += ["## Category errors", "", "| expected | actual | n |", "|---|---|---|"]
        out += [f"| {c['expected']} | {c['actual']} | {c['count']} |"
                for c in report["confusion"]]
        out.append("")
    if report["failures"]:
        out += ["## Hard failures", "", "| ticket | attempts | error |", "|---|---|---|"]
        out += [f"| {f['ticket_id']} | {f['attempts']} | {f['error']} |"
                for f in report["failures"]]
        out.append("")

    out += ["## Every ticket", "",
            "| ticket | input (trimmed) | expected | actual | pass |",
            "|---|---|---|---|---|"]
    for row in report["rows"]:
        text = WS.sub(" ", row["text"])[:110].replace("|", "/")
        expected = f"{row['expected']['category']} P{row['expected']['priority']} " \
                   f"{row['expected']['next_step']}"
        actual = f"{row['actual']['category']} P{row['actual']['priority']} " \
                 f"{row['actual']['next_step']}"
        marks = "".join(("C" if row["category_ok"] else "c",
                         "P" if row["priority_ok"] else "p",
                         "S" if row["next_step_ok"] else "s"))
        verdict = "PASS" if marks == "CPS" else f"fail ({marks})"
        out.append(f"| {row['ticket_id']} | {text} | {expected} | {actual} | {verdict} |")
    out += ["",
            "Upper case = that field matched: C category, P priority, S next_step.",
            ""]
    return "\n".join(out)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", help="a file written by scripts/triage.py")
    parser.add_argument("--compare", default=None,
                        help="an earlier run: prints the tickets that flipped, "
                             "which is the regression diff the eval lecture asks "
                             "for - an accuracy that held while half the answers "
                             "changed is not the same system")
    args = parser.parse_args()

    with open(args.run, encoding="utf-8") as handle:
        run = json.load(handle)
    report = score(run)
    s = report["summary"]

    stem = os.path.splitext(os.path.basename(args.run))[0]
    results_dir = os.path.join(ROOT, "eval", "results")
    os.makedirs(results_dir, exist_ok=True)
    with open(os.path.join(results_dir, f"{stem}.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    with open(os.path.join(results_dir, f"{stem}.md"), "w", encoding="utf-8") as handle:
        handle.write(markdown(report))

    report_to_console(report)
    if args.compare:
        compare_to_console(report, args.compare)
    print(f"wrote eval/results/{stem}.md and .json")


def report_to_console(report: dict) -> None:
    s = report["summary"]
    print(f"{s['set']} / {s['prompt_version']} / {s['model']}")
    print(f"  category   {s['category_accuracy']:.0%}  macro F1 {s['macro_f1']:.2f}"
          f"  core F1 {s['macro_f1_core']:.2f} ({s['core_classes']} classes)")
    print(f"  macro P/R  {s['macro_precision']:.2f} / {s['macro_recall']:.2f}"
          f"   core P/R {s['macro_precision_core']:.2f} / "
          f"{s['macro_recall_core']:.2f}")
    print(f"  priority   {s['priority_accuracy']:.0%}")
    print(f"  next_step  {s['next_step_accuracy']:.0%}")
    print(f"  all three  {s['all_three_accuracy']:.0%}")
    print(f"  secondary  {s['secondary_jaccard']:.0%} Jaccard")
    print(f"  evidence   {s['evidence_verbatim_rate']:.0%} verbatim")
    print(f"  confidence {_fmt(s['confidence_when_right'])} right / "
          f"{_fmt(s['confidence_when_wrong'])} wrong")
    print(f"  failures   {s['hard_failures']} hard, {s['repaired']} repaired")
    print(f"  cost       ${s['cost_per_ticket']:.5f}/ticket = "
          f"${s['cost_per_10k']:.2f}/10k")
    esc = s.get("escalation") or {}
    if esc:
        print(f"  escalation {esc['precision']:.0%} precision / "
              f"{esc['recall']:.0%} recall  (missed {esc['fn']}, "
              f"spurious {esc['fp']})")
    for cut, groups in (report.get("buckets") or {}).items():
        print(f"  by {cut}: " + "  ".join(
            f"{value} {row['category']:.0%} (n={row['n']})"
            for value, row in groups.items()))
    if report["confusion"]:
        print("  category errors:")
        for c in report["confusion"]:
            print(f"    {c['expected']} -> {c['actual']}  x{c['count']}")

def compare_to_console(report: dict, path: str) -> None:
    if True:
        with open(path, encoding="utf-8") as handle:
            other = score(json.load(handle))
        before = {r["ticket_id"]: r for r in other["rows"]}
        flips = [(r, before[r["ticket_id"]]) for r in report["rows"]
                 if r["ticket_id"] in before
                 and r["actual"]["category"] != before[r["ticket_id"]]["actual"]["category"]]
        gained = [f for f in flips if f[0]["category_ok"] and not f[1]["category_ok"]]
        lost = [f for f in flips if not f[0]["category_ok"] and f[1]["category_ok"]]
        print()
        print(f"vs {os.path.basename(path)}: {len(flips)} categories "
              f"changed, {len(gained)} fixed, {len(lost)} broken, "
              f"{len(flips) - len(gained) - len(lost)} wrong both ways")
        for now, was in flips:
            mark = "FIXED " if now["category_ok"] else ("BROKE " if was["category_ok"]
                                                       else "      ")
            print(f"  {mark}{now['ticket_id']:18} {was['actual']['category']:22}"
                  f" -> {now['actual']['category']:22} (label "
                  f"{now['expected']['category']})")


if __name__ == "__main__":
    main()
