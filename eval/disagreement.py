"""Where every model agrees and the label disagrees, suspect the label.

    python eval/disagreement.py --set dev
    python eval/disagreement.py --set dev --field priority --min-models 2

WHY THIS IS A DIFFERENT INSTRUMENT FROM scripts/audit_labels.py
    That one checks each label against a necessary condition written by hand:
    cancellation_failed must contain a cancellation attempt, and so on. It finds
    labels that contradict the rules. It cannot find a label that follows the
    rules and is still wrong, because it only knows what we already thought.

    This one uses the models as independent readers. When five runs of
    gpt-4.1-mini and three of gpt-5-mini - different architectures, different
    training, one prompt - all read a ticket the same way and that way is not
    ours, the cheap explanation is that they are all wrong together and the
    expensive one is that we mislabelled it. The second explanation is worth
    checking, and 4 of 51 flags in the first audit turned out to be real errors.

THE RULE THIS TOOL DOES NOT BREAK
    A consensus is a FLAG, not a verdict. The verdict comes from the labelling
    rules in the label dictionary, applied by hand, and every change is recorded
    with its reason. Changing a label because a model disagreed is how a test set
    quietly becomes a mirror of the model it was supposed to judge - and the
    cheapest way to reach 100% accuracy on a benchmark that then means nothing.

WHAT IS PRINTED
    UNANIMOUS   every run of every model says X, the label says Y. Read these.
    MAJORITY    most runs say X. Usually a genuinely ambiguous ticket.
    SPLIT       the runs disagree with each other. That is model noise, not a
                label problem, and it belongs in the error analysis instead.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter

# A quarter of both sets is not English and 8% is not Latin script, and the
# Windows console is cp1251 here: printing a Turkish or Japanese ticket raised
# UnicodeEncodeError and killed the report halfway through the first finding.
# The terminal gets replacements, the file on disk gets the real text.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "data", "runs")


def load_labels(set_name: str) -> dict[str, dict]:
    with open(os.path.join(ROOT, "data", "tickets", f"{set_name}.json"),
              encoding="utf-8") as handle:
        return {t["ticket_id"]: t for t in json.load(handle)}


def load_runs(set_name: str, versions: list[str]) -> list[dict]:
    out = []
    for path in sorted(glob.glob(os.path.join(RUNS, f"{set_name}__*.json"))):
        with open(path, encoding="utf-8") as handle:
            run = json.load(handle)
        if len(run.get("results", [])) < 50:
            continue
        version = str(run.get("prompt_version", ""))
        if versions and not any(version == v or version.startswith(v + "-")
                                for v in versions):
            continue
        out.append(run)
    return out


def analyse(set_name: str, field: str, versions: list[str],
            min_models: int = 2) -> tuple[list[str], dict[str, list], str | None]:
    """The whole audit as a function, so the benchmark can run it on the runs it
    has just written without a second set of API calls. Returns the report lines,
    the three buckets, and the path it wrote - or (message, {}, None) when there
    is nothing to read."""
    labels = load_labels(set_name)
    runs = load_runs(set_name, versions)
    if not runs:
        return ([f"no {set_name} runs for versions {','.join(versions)}"], {}, None)

    lines: list[str] = []

    def say(text: str = "") -> None:
        lines.append(text)

    say(f"# Model consensus against our labels: {set_name}, {field}")
    say()
    say(f"{len(runs)} runs, {len({r['model'] for r in runs})} distinct models: "
        + ", ".join(sorted({f"{r['model']} ({r.get('prompt_version')})"
                            for r in runs})))

    votes: dict[str, list[tuple[str, str]]] = {}
    for run in runs:
        for row in run["results"]:
            triage = row.get("triage")
            if not triage:
                continue
            votes.setdefault(row["ticket_id"], []).append(
                (run["model"], str(triage[field])))

    buckets: dict[str, list] = {"UNANIMOUS": [], "MAJORITY": [], "SPLIT": []}
    for ticket_id, cast in sorted(votes.items()):
        gold = str(labels[ticket_id]["label"][field])
        counts = Counter(value for _, value in cast)
        top, hits = counts.most_common(1)[0]
        if top == gold:
            continue
        if len({model for model, value in cast if value == top}) < min_models:
            continue
        share = hits / len(cast)
        bucket = ("UNANIMOUS" if hits == len(cast)
                  else "MAJORITY" if share >= 0.6 else "SPLIT")
        buckets[bucket].append((ticket_id, gold, top, hits, len(cast), counts))

    for bucket in ("UNANIMOUS", "MAJORITY", "SPLIT"):
        say()
        say(f"## {bucket}: {len(buckets[bucket])} tickets")
        for ticket_id, gold, top, hits, total, counts in buckets[bucket]:
            ticket = labels[ticket_id]
            text = " ".join(ticket["text"].split())
            say()
            say(f"### {ticket_id} - labelled `{gold}`, models say `{top}` "
                f"({hits}/{total})")
            if len(counts) > 1:
                say("votes: " + ", ".join(f"{k} x{v}"
                                          for k, v in counts.most_common()))
            say(f"> {text[:700]}{'...' if len(text) > 700 else ''}")
            secondary = ticket["label"].get("secondary_categories")
            if field == "category" and secondary:
                say(f"our secondary: {secondary}")
            say(f"our rationale: {ticket['label'].get('rationale', '')[:300]}")
            for run in runs:
                hit = next((row for row in run["results"]
                            if row["ticket_id"] == ticket_id and row.get("triage")
                            and str(row["triage"][field]) == top), None)
                if hit:
                    say(f"their reason ({run['model']}): "
                        f"{hit['triage']['rationale'][:300]}")
                    break

    flagged = sum(len(v) for v in buckets.values())
    say()
    say(f"{flagged} of {len(votes)} tickets flagged on {field}: "
        f"{len(buckets['UNANIMOUS'])} unanimous, {len(buckets['MAJORITY'])} "
        f"majority, {len(buckets['SPLIT'])} split. A flag is a question, not a "
        f"verdict - adjudicate against the label dictionary.")

    path = os.path.join(ROOT, "eval", "results",
                        f"disagreement__{set_name}__{field}.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return lines, buckets, path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", default="dev", choices=["dev", "golden"])
    parser.add_argument("--field", default="category",
                        choices=["category", "priority", "next_step"])
    parser.add_argument("--versions", default="v8,s1",
                        help="comma separated prompt versions to trust; v1 at 58% "
                             "accuracy is not a reader worth consulting")
    parser.add_argument("--min-models", type=int, default=2,
                        help="distinct models that must agree before a label is "
                             "flagged - one model agreeing with itself is one "
                             "opinion repeated, not two")
    args = parser.parse_args()

    lines, buckets, path = analyse(
        args.set, args.field, [v for v in args.versions.split(",") if v],
        args.min_models)
    for line in lines:
        print(line)
    if path:
        print()
        print(f"wrote {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
