"""Draft the retrieval answer key. The model proposes, the engineer decides.

    python benchmark/label_gold.py                 # all of benchmark/tickets.csv
    python benchmark/label_gold.py --limit 20      # stratified smoke run
    python benchmark/label_gold.py --full-kb       # every document, no shortlist

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

WHY NOT THE WHOLE KNOWLEDGE BASE IN EVERY CALL
    An earlier draft of this script sent all 73 documents - 26.4k tokens - with
    every ticket, so that nothing could hide behind a category prior. It was
    twenty times the input for a choice that is really between five and seven
    documents, and it made the model find a needle in a haystack we had built
    ourselves.

    The prompt carries the full text of the CANDIDATES for the ticket's category
    and the TITLE of every document in the base. The prior stays escapable: a
    ticket answered by something outside its category comes back with that title
    in `outside`, and those go to a human.

    Titles travel WITHOUT their ids, and that is the whole of the fix v2 made.
    v1 printed the catalogue as "[id] Title", and the model duly answered with
    ids for documents whose body it had never been shown: five of the seven
    unverifiable quotes in the first pilot were invented for exactly those
    documents, in the confident register such a document usually uses. A name it
    cannot cite is a name it cannot smuggle into the answer.

    --full-kb sends all 73 bodies and drops the catalogue, so the shortlist can
    be argued against with a measurement instead of a claim.

WHY THE EVIDENCE SPAN
    A document id cannot be checked by looking at it - a wrong one and a right
    one are both eight characters. A sentence copied out of the document can be
    checked by string search, and more usefully it lets the engineer confirm a
    row without opening the source at all. Rows whose evidence is not found are
    marked rather than silently kept.
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


class Draft(BaseModel):
    doc_ids: list[str]
    evidence: str
    why: str
    outside: str


SCHEMA = {
    "name": "gold_draft",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["doc_ids", "evidence", "why", "outside"],
        "properties": {
            "doc_ids": {"type": "array", "items": {"type": "string"}},
            "evidence": {"type": "string"},
            "why": {"type": "string"},
            "outside": {"type": "string"},
        },
    },
}

SPACE = re.compile(r"\s+")


def flat(text: str) -> str:
    """Compare spans without punishing the model for re-wrapping a line."""
    return SPACE.sub(" ", text).strip().lower()


def catalogue(docs: list) -> str:
    """Titles with no ids: a document the model cannot name it cannot fake."""
    return "\n".join(d.title for d in docs)


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
    ap.add_argument("--prompt", default="v2")
    ap.add_argument("--full-kb", action="store_true",
                    help="send every document instead of the category shortlist")
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
    every = [d.id for d in docs] if args.full_kb else None
    system = (PROMPTS / f"{args.prompt}.md").read_text(encoding="utf-8")
    if every is None:
        system += "\n\n## CATALOGUE\n\n" + catalogue(docs)
    prompt = config.PromptConfig(
        version=f"label_gold/{args.prompt}", model=args.model, temperature=0.0,
        response_format="json_schema", text_override=system,
        change_reason="gold drafting prompt")

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
            "outside": d.get("outside", ""),
            "why": d.get("why", ""),
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
    outside: list[tuple] = []
    proposed_none: list[str] = []
    disagreed: list[str] = []
    failed: list[str] = []

    for tid, got in drafts.items():
        row = by_ticket[tid]
        if got["draft"] is None:
            failed.append(tid)
            continue
        d = got["draft"]
        ids = d["doc_ids"]
        unknown += [(tid, i) for i in ids if i not in set(got["shown"])]
        if d["outside"]:
            outside.append((tid, d["outside"]))
        if not ids:
            proposed_none.append(tid)
        else:
            first = by_id.get(ids[0])
            found = bool(first and d["evidence"]
                         and flat(d["evidence"]) in flat(first.body))
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
    print(f"  proposed none: {len(proposed_none)} "
          f"({len(proposed_none) / total:.0%})"
          "   <- near 0% or near 100% means the prompt is broken")
    print(f"  ids it was never shown: {len(unknown)}   <- must be 0")
    print(f"  evidence not found in the document: {len(unfound)}"
          "   <- marked in the csv, not trusted")
    print(f"  pointed outside the shortlist: {len(outside)}"
          "   <- a count, not an error: the shortlist is only a prior")
    print(f"  found an answer where the labelling says escalate: "
          f"{len(disagreed)}   <- real disagreements, read these")
    print(f"  calls that never returned: {len(failed)}")
    for tid, title in outside[:12]:
        print(f"      outside:      {tid} -> {title[:58]}")
    for tid in disagreed[:10]:
        print(f"      disagreement: {tid}")


if __name__ == "__main__":
    main()
