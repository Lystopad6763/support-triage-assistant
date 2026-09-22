"""Run the agent assistant over tickets and measure what it produced.

    python eval/assist.py --limit 20
    python eval/assist.py --limit 20 --model openai/gpt-5-mini

WHAT IS CHECKED, AND WHY EACH ONE IS MECHANICAL
    The assignment asks for the failures of tone variation, not only the
    method. A failure nobody can see is not reported, so every check here runs
    without a human and produces a number.

        citation    the quoted sentence exists, word for word, in the document
                    it names, and that document is one retrieval returned. A
                    citation the agent clicks and cannot find is worse than no
                    citation, because it spends their trust once.

        banned      seven phrases the knowledge base forbids, each with the
                    policy that forbids it. The prompt asks; this verifies.

        similarity  the three tones compared against each other. One reply
                    rewritten three times reads like three until it is
                    measured - this is the number that says whether the agent
                    has a choice or a decoration.

        shape       a concise reply of six sentences is not concise, and a
                    formal one without a greeting is not formal. The prompt
                    describes three incompatible shapes; these assert them.

    Structure is checked separately from similarity on purpose: three replies
    can be textually different and still all be the same shape, which is the
    subtler failure and the one prose in a prompt does not prevent.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import assist, config                         # noqa: E402

TICKETS = ROOT / "benchmark" / "tickets.csv"
OUT = ROOT / "eval" / "results"

SENTENCE = re.compile(r"[.!?]+(?:\s|$)")
GREETING = re.compile(r"^\s*(hello|hi|dear|good (morning|afternoon|evening))",
                      re.I)
SIGNOFF = re.compile(r"(best regards|kind regards|sincerely|warm regards|"
                     r"best wishes|regards,|the nebula team|nebula team)",
                     re.I)
# Phrases the prompt bans from the empathetic variant by name. They are not in
# BANNED in app/assist.py because they are not unsafe - they are empty, which
# is a different failure and belongs to tone rather than to policy.
FILLER = re.compile(
    r"(we understand your frustration|apolog\w+ for any inconvenience|"
    r"we value your feedback|thank you for your patience|rest assured)", re.I)


def sentences(text: str) -> int:
    return len([s for s in SENTENCE.split(text.strip()) if s.strip()])


def shape(out) -> dict:
    """Did each variant come out in the shape it was asked for?"""
    return {
        "concise_le_3_sentences": sentences(out.concise) <= 3,
        "concise_has_no_greeting": not GREETING.search(out.concise),
        "concise_has_no_signoff": not SIGNOFF.search(out.concise),
        "formal_has_greeting": bool(GREETING.search(out.formal)),
        "formal_has_signoff": bool(SIGNOFF.search(out.formal)),
        "empathetic_no_greeting_first": not GREETING.search(out.empathetic),
        "empathetic_no_filler": not FILLER.search(out.empathetic),
    }


def one(row: dict, engine: assist.Engine) -> dict:
    result = engine.draft(row["original"])
    o = result.output
    record = {
        "id": row["id"], "lang": row["lang"], "category": row["category"],
        "expects_none": bool(row["expects_none"]),
        "error": result.error,
        "retrieval_ms": result.retrieval_ms,
        "generation_ms": result.generation_ms,
        "cost_usd": round(result.cost_usd, 6),
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "retrieved": [s.doc_id for s in result.sources],
    }
    if o is None:
        return record
    record.update({
        "summary": o.summary,
        "grounded": o.grounded,
        "needs_human": o.needs_human,
        "needs_human_reason": o.needs_human_reason,
        "citation_doc_id": o.citation_doc_id,
        "citation_quote": o.citation_quote,
        "citation_ok": result.citation_ok,
        "banned": result.banned,
        "similarity": result.similarity,
        "shape": shape(o),
        "lengths": {t: len(getattr(o, t)) for t in assist.TONES},
        "sentences": {t: sentences(getattr(o, t)) for t in assist.TONES},
        **{t: getattr(o, t) for t in assist.TONES},
    })
    return record


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--model", default=assist.MODEL)
    ap.add_argument("--prompt", default=assist.VERSION)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    rows = list(csv.DictReader(TICKETS.open(encoding="utf-8-sig"),
                               delimiter=";"))
    # Spread over language and category rather than taking the first N, which
    # in a file sorted by category would be twenty of one complaint.
    step = max(1, len(rows) // args.limit)
    rows = rows[::step][:args.limit]

    settings = config.load()
    engine = assist.Engine(settings, args.model, args.prompt)
    print(f"{len(rows)} tickets, {args.model}")

    got = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for record in pool.map(lambda r: one(r, engine), rows):
            got.append(record)
            if len(got) % 10 == 0:
                print(f"  {len(got)}/{len(rows)}", flush=True)

    report(got, args.model)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"assist_{stamp}.json"
    path.write_text(json.dumps(
        {"run": stamp, "model": args.model, "prompt": f"assist/{args.prompt}",
         "drafts": got}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n-> {path.relative_to(ROOT)}")


def report(got: list[dict], model: str) -> None:
    ok = [g for g in got if "summary" in g]
    n = len(ok)
    if not n:
        print("every call failed")
        return
    print(f"\n{n}/{len(got)} returned an object, {model}")
    print(f"  cost per ticket: ${statistics.mean(g['cost_usd'] for g in ok):.5f}"
          f"   -> 10k/month ${statistics.mean(g['cost_usd'] for g in ok) * 10000:.2f}")
    print(f"  latency p50: {statistics.median(g['retrieval_ms'] + g['generation_ms'] for g in ok):.0f} ms"
          f"  (retrieval {statistics.median(g['retrieval_ms'] for g in ok):.0f}"
          f" + generation {statistics.median(g['generation_ms'] for g in ok):.0f})")

    print(f"\n  citation verified in the named document: "
          f"{sum(g['citation_ok'] for g in ok)}/{n}")
    print(f"  grounded=true: {sum(g['grounded'] for g in ok)}/{n}"
          f"   needs_human=true: {sum(g['needs_human'] for g in ok)}/{n}")
    banned = [(g['id'], b) for g in ok for b in g["banned"]]
    print(f"  banned phrases: {len(banned)}")
    for tid, b in banned[:6]:
        print(f"      {tid}: {b}")

    print("\n  tone similarity (1.0 = identical text)")
    for pair in ("formal~empathetic", "formal~concise", "empathetic~concise"):
        vals = [g["similarity"][pair] for g in ok]
        worst = max(ok, key=lambda g: g["similarity"][pair])
        print(f"      {pair:<20} mean {statistics.mean(vals):.3f}   "
              f"max {max(vals):.3f} ({worst['id']})")

    print("\n  shape, how many of the three came out as asked")
    checks = list(ok[0]["shape"])
    for check in checks:
        passed = sum(g["shape"][check] for g in ok)
        flag = "" if passed == n else "   <-"
        print(f"      {check:<32} {passed:>3}/{n}{flag}")

    print("\n  length in sentences (median)")
    for tone in assist.TONES:
        vals = [g["sentences"][tone] for g in ok]
        print(f"      {tone:<12} {statistics.median(vals):.0f}"
              f"   range {min(vals)}-{max(vals)}")


if __name__ == "__main__":
    main()
