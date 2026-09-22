"""Draft the retrieval answer key. The model proposes, the engineer decides.

    python benchmark/label_gold.py                 # all of benchmark/tickets.csv
    python benchmark/label_gold.py --limit 20      # stratified smoke run
    python benchmark/label_gold.py --shortlist     # category pool, measured worse

WHY A DRAFT AND NOT A LABEL
    recall@k is the share of tickets whose CORRECT document came back, so
    "correct" has to be decided by something that is not the retriever. If the
    answer key were built by searching, we would keep the tickets the search
    already finds and then measure the search on them: the number would come out
    high by construction and would mean nothing.

    The obvious alternative - let a model decide and trust it - trades one
    problem for another, because then the key itself has to be validated, and
    validating it means labelling a sample by hand anyway. So the model does not
    decide. It proposes a document and copies out the sentence that justifies
    it, and the engineer confirms or corrects. The labels are his; there is
    nothing left to calibrate.

    What that buys is the difference between "read 73 documents and choose" and
    "agree or correct one proposal with its quote already under it".

WHY THE WHOLE KNOWLEDGE BASE, AFTER ARGUING THE OPPOSITE
    This script first sent only the five to seven documents of the ticket's
    category, on the reasoning that 73 documents is a haystack we would be
    building ourselves. That reasoning was wrong, and the pilot said so: run
    both ways over the same 20 tickets, the two modes agreed on the first
    document 8 times out of 20 and on the whole set 4 times.

    The shortlist lost. Six price_not_expected tickets in a row were assigned
    pol-18, because pol-18 was the only refund document that pool contained; the
    whole base gave those same tickets pol-04, pol-14 and the cancellation
    article, one each, correctly. A French ticket reading "Me desabonner" -
    unsubscribe me - was sent to "How to access my report" because its category
    was nothing_delivered. On all 430 tickets, the key for a whole category
    would have collapsed onto one document, and every retriever would then have
    been scored against it.

    The pools were written by reading the knowledge base, not by reading the
    tickets, and the category names flattered them: price_not_expected is mostly
    a trial that converted, not a question about prices.

    It costs $0.87 instead of $0.44 across 430 tickets. Six times the tokens,
    twice the money - the provider's prompt cache absorbs the rest - and about
    300ms more per call. --shortlist keeps the old behaviour so the comparison
    can be re-run rather than taken on trust.

WHY THE EVIDENCE SPAN
    A document id cannot be checked by looking at it - a wrong one and a right
    one are both eight characters. A sentence copied out of the document can be
    checked by string search, and more usefully it lets the engineer confirm a
    row without opening the source at all. Rows whose evidence is not found are
    marked rather than silently kept.

    It is searched for in EVERY named document, not only the first. The four
    spans the pilot could not place were all real knowledge base text filed
    under the wrong id: "Deleting the app does not cancel your subscription"
    lives in pol-04 and pol-16, while the model attributed it to the article
    named "How to cancel subscription?" - the obvious home of the topic, whose
    body is actually a numbered click-path. Checking one document called that a
    fabrication. It was an attribution.

WHY THE KEY IS A SET AND NOT ONE DOCUMENT
    That same overlap decides the metric. If three documents carry one answer,
    scoring recall against a single chosen id marks a retriever wrong for
    returning one of the other two - though the agent reading it would have
    closed the ticket. So `doc_ids` is every document that carries the answer,
    most direct first, and a hit is any member of that set inside the top k.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import config, kb, llm                      # noqa: E402

HERE = Path(__file__).resolve().parent
TICKETS = HERE / "tickets.csv"
PROMPTS = ROOT / "prompts" / "label_gold"

# Any competent multilingual model does this job, because its output is a draft
# and not a verdict. This one is chosen for the widest structured-output support
# among the probed endpoints (8 of 8 in data/model_params.json) and for costing
# little across 430 calls. Swapping it changes proposals, never labels.
MODEL = "google/gemini-3.1-flash-lite"
WORKERS = 8
NON_LATIN = {"arabic", "hangul", "han", "cyrillic", "thai"}


# The lecture's prompt-metadata block, kept OUT of the .md on purpose: the
# prompt file is spoken to the model on every call, and a change_reason sitting
# inside it is an instruction the model will try to follow. It lives here until
# config.PROMPTS stops being hardcoded to prompts/classify.
VERSIONS = {
    "v1": {
        "created": "2026-09-22", "author": "serhii",
        "change_reason": "first draft: category pool in full, whole catalogue "
                         "as [id] Title, confidence field",
        "previous_version": None,
        "tested_on": "20 stratified tickets",
        "result": "7 of 20 evidence spans not in the named document; "
                  "16 ids named from outside the pool; confidence 'high' 20/20",
    },
    "v2": {
        "created": "2026-09-22", "author": "serhii",
        "change_reason": "catalogue loses its ids, so a document whose body was "
                         "never shown cannot be cited; confidence dropped for "
                         "carrying one value",
        "previous_version": "v1",
        "tested_on": "the same 20",
        "result": "evidence misses 7 -> 4; out-of-pool ids 16 -> 1",
    },
    "v3": {
        "created": "2026-09-22", "author": "serhii",
        "change_reason": "whole knowledge base instead of the category pool, "
                         "after the pool lost a head-to-head; key becomes a set "
                         "because the base states one answer in several places",
        "previous_version": "v2",
        "tested_on": "the same 20",
        "result": "evidence misses 4 -> 0; but keys averaged 3.1 documents, "
                  "6 of 20 naming four, which lifts the random floor of "
                  "recall@5 from 6.8% to 25.2%",
    },
    "v5": {
        "created": "2026-09-22", "author": "serhii",
        "change_reason": "one change only: the reasoning field no longer asks "
                         "what an agent must tell them, which presupposed "
                         "there was something to tell and cost v4 every "
                         "abstention it should have kept",
        "previous_version": "v4",
        "tested_on": "the same 20",
        "result": None,
    },
    "v4": {
        "created": "2026-09-22", "author": "serhii",
        "change_reason": "reasoning moves to the first schema field so the "
                         "model works before it commits rather than justifying "
                         "afterwards; three worked examples replace the prose "
                         "about when several documents are right",
        "previous_version": "v3",
        "tested_on": "the same 20",
        "result": None,
    },
}


class Draft(BaseModel):
    # Field order is generation order under a strict schema, so reasoning first
    # is the whole of the chain-of-thought here: last, it could only ever be a
    # justification of a choice already written.
    reasoning: str
    doc_ids: list[str]
    evidence: str


SCHEMA = {
    "name": "gold_draft",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["reasoning", "doc_ids", "evidence"],
        "properties": {
            "reasoning": {"type": "string"},
            "doc_ids": {"type": "array", "items": {"type": "string"}},
            "evidence": {"type": "string"},
        },
    },
}

SPACE = re.compile(r"\s+")


def flat(text: str) -> str:
    """Compare spans without punishing the model for re-wrapping a line."""
    return SPACE.sub(" ", text).strip().lower()


def candidates(ids: list[str], by_id: dict) -> str:
    return "\n\n---\n\n".join(
        f"[{by_id[i].id}] {by_id[i].title}\n{by_id[i].body}" for i in ids)


def stratified(rows: list[dict], limit: int) -> list[dict]:
    """A smoke run should hit the hard rows, not the first twenty.

    Every category, the tickets labelled as having no KB answer, the ones whose
    text names another rail, the non-Latin scripts and the longest input -
    because those are where a labelling prompt breaks, and the first twenty rows
    of a file sorted by store are twenty variations of one English complaint.
    """
    picked: dict[str, dict] = {}

    def take(subset: list[dict], n: int) -> None:
        for row in subset[:n]:
            picked.setdefault(row["id"], row)

    for cat in sorted({r["category"] for r in rows}):
        take([r for r in rows if r["category"] == cat], 2)
    take([r for r in rows if r["expects_none"]], 2)
    take([r for r in rows if r["rail_uncertain"]], 2)
    take([r for r in rows if r["lang"] in NON_LATIN], 3)
    take(sorted(rows, key=lambda r: -len(r["original"])), 2)
    take([r for r in rows if r["synthetic"]], 2)
    take(rows, max(0, limit - len(picked)))
    return list(picked.values())[:limit]


def label(row: dict, system: str, prompt, settings, by_id: dict,
          every: list[str] | None = None) -> dict:
    result = llm.Result(ticket_id=row["id"], model=prompt.model)
    shown = every if every is not None else row["shortlist"].split()
    user = (f"CANDIDATES\n\n{candidates(shown, by_id)}\n\n"
            f"=== TICKET ===\n\n{row['original']}")
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    started = time.monotonic()
    draft = llm.run(messages, result, prompt, settings,
                    schema=SCHEMA, model_cls=Draft)
    return {
        "id": row["id"],
        "draft": draft.model_dump() if draft else None,
        "error": result.error,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost_usd": getattr(result, "cost_usd", 0.0),
        "shown": shown,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="stratified subset; 0 means every ticket")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--prompt", default="v5")
    ap.add_argument("--shortlist", action="store_true",
                    help="send only the category pool; measured worse, kept so "
                         "that finding can be reproduced")
    ap.add_argument("--out", default="gold",
                    help="basename for the csv and json written beside this file")
    args = ap.parse_args()

    docs = kb.indexed(kb.verify())
    by_id = {d.id: d for d in docs}
    rows = list(csv.DictReader(TICKETS.open(encoding="utf-8-sig"),
                               delimiter=";"))
    if args.limit:
        rows = stratified(rows, args.limit)
    # Grouped so the candidate block repeats across consecutive calls: there are
    # six distinct blocks for 430 tickets, and a provider that caches a prefix
    # can only do it when the prefix actually repeats.
    rows.sort(key=lambda r: (r["category"], r["id"]))

    settings = config.load()
    every = None if args.shortlist else [d.id for d in docs]
    system = (PROMPTS / f"{args.prompt}.md").read_text(encoding="utf-8")
    meta = VERSIONS.get(args.prompt, {})
    prompt = config.PromptConfig(
        version=f"label_gold/{args.prompt}", model=args.model, temperature=0.0,
        response_format="json_schema", text_override=system,
        previous_version=meta.get("previous_version"),
        tested_on=meta.get("tested_on", "unrecorded"),
        change_reason=meta.get("change_reason", "unrecorded"))

    shape = "every document" if every else "category shortlist"
    print(f"{len(rows)} tickets, {args.model}, prompt {args.prompt}, "
          f"{shape}, system {len(system):,} chars")
    out: list[dict] = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(label, r, system, prompt, settings, by_id, every)
                   for r in rows]
        for future in futures:
            out.append(future.result())
            if len(out) % 25 == 0 or len(out) == len(rows):
                spent = sum(r["cost_usd"] for r in out)
                print(f"  {len(out)}/{len(rows)}  ${spent:.4f}", flush=True)

    drafts = {r["id"]: r for r in out}
    report(rows, drafts, by_id)
    write(rows, drafts, args.out)


def write(rows: list[dict], drafts: dict, base: str = "gold") -> None:
    out = []
    for row in rows:
        got = drafts[row["id"]]
        d = got["draft"] or {}
        ids = d.get("doc_ids", [])
        proposed = " ".join(ids) if ids else "none"
        out.append({
            "id": row["id"],
            "set": row["set"],
            "synthetic": row["synthetic"],
            "lang": row["lang"],
            "category": row["category"],
            "store": row["store"],
            "rail_uncertain": row["rail_uncertain"],
            "expects_none": row["expects_none"],
            # Pre-filled with the proposal so that agreeing costs no keystrokes
            # and only a correction does. `proposed` keeps the original, so how
            # often the draft was overridden becomes a number we can report
            # instead of a feeling.
            "gold": proposed,
            "proposed": proposed,
            "evidence": d.get("evidence", ""),
            "evidence_found": row.get("_evidence_found", ""),
            "reasoning": d.get("reasoning", ""),
            "error": got["error"] or "",
            "note": "",
            "original": row["original"],
        })
    out_csv = HERE / f"{base}.csv"
    out_json = HERE / f"{base}_draft.json"
    with out_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(out)
    out_json.write_text(json.dumps(list(drafts.values()), ensure_ascii=False,
                                   indent=2), encoding="utf-8")
    print(f"\n{len(out)} rows -> {out_csv.relative_to(ROOT)}")
    print(f"raw drafts   -> {out_json.relative_to(ROOT)}")


def report(rows: list[dict], drafts: dict, by_id: dict) -> None:
    """Five checks that need no human, run before the human starts."""
    by_ticket = {r["id"]: r for r in rows}
    unknown: list[tuple] = []
    unfound: list[str] = []
    proposed_none: list[str] = []
    disagreed: list[str] = []
    failed: list[str] = []
    sizes: list[int] = []

    for tid, got in drafts.items():
        row = by_ticket[tid]
        if got["draft"] is None:
            failed.append(tid)
            continue
        d = got["draft"]
        ids = d["doc_ids"]
        unknown += [(tid, i) for i in ids if i not in set(got["shown"])]
        if not ids:
            proposed_none.append(tid)
        else:
            sizes.append(len(ids))
            # Searched in every named document, not only the first: the base
            # says the same thing in several places, and a span filed under the
            # neighbouring id is an attribution, not a fabrication.
            span = flat(d["evidence"])
            found = bool(span and any(
                span in flat(by_id[i].body) for i in ids if i in by_id))
            row["_evidence_found"] = "yes" if found else "no"
            if not found:
                unfound.append(tid)
        if row["expects_none"] and ids:
            disagreed.append(tid)

    total = len(drafts)
    spent = sum(r["cost_usd"] for r in drafts.values())
    tokens = sum(r["input_tokens"] for r in drafts.values())
    latency = sorted(r["latency_ms"] for r in drafts.values())
    print(f"\n{total} drafted, ${spent:.4f}, {tokens:,} input tokens")
    print(f"  median latency: {latency[len(latency) // 2]} ms")
    counts = {n: sizes.count(n) for n in sorted(set(sizes))}
    print(f"  documents per key: {counts}   <- all 1s means the set never "
          "formed")
    print(f"  proposed none: {len(proposed_none)} "
          f"({len(proposed_none) / total:.0%})"
          "   <- near 0% or near 100% means the prompt is broken")
    print(f"  ids it was never shown: {len(unknown)}   <- must be 0")
    print(f"  evidence not found in the document: {len(unfound)}"
          "   <- marked in the csv, not trusted")
    print(f"  found an answer where the labelling says escalate: "
          f"{len(disagreed)}   <- real disagreements, read these")
    print(f"  calls that never returned: {len(failed)}")
    for tid in disagreed[:10]:
        print(f"      disagreement: {tid}")


if __name__ == "__main__":
    main()
