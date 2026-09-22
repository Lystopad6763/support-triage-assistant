"""Score every retrieval design on the same queries, and write the table.

    python eval/retrieval.py                  # all 14 cells
    python eval/retrieval.py --limit 40       # a quick pass over the first 40

WHAT IS BEING DECIDED
    chunking   article (73 chunks) or section (131)
    encoder    baai/bge-m3, openai/text-embedding-3-small, qwen3-embedding-8b
    retrieval  BM25, dense, or the two fused with RRF

    Seven methods per chunking, because BM25 does not depend on an encoder:
    one lexical cell, three dense, three hybrid. Fourteen in all, on identical
    queries - measured apart, they would compare sets of queries instead of
    designs.

MEASURED AT DOCUMENT LEVEL, DEEPER THAN k
    The key names documents, and a citation names a document, so a hit on
    hc-28900802305297#3 is a hit on hc-28900802305297. That also makes the two
    chunkings comparable at all: five section chunks can be three documents,
    while five article chunks are always five.

    So each cell retrieves chunks generously and rolls them up until it has k
    distinct documents. How many chunks that took is reported as `chunks@5`,
    because it is the real context cost: the section index buying its five
    documents with nine chunks is sending nine chunks to the model.

TWO RECALLS, AND WHY BOTH ARE PRINTED
    The key is a set - the base states one answer in several places, so any
    member is a correct return. But it is an ORDERED set, and its first entry
    is a judgment: two strong models, run over the same twenty tickets, picked
    the same first document only 13 times.

        lenient   any member of the key inside the top k. Robust: it barely
                  moves when the key is rebuilt by a different model.
        strict    the key's first document inside the top k. It depends on
                  that 65% agreement, so it is a diagnostic and not a headline.

    Lenient has the higher floor - with a three-document key, five of
    seventy-three documents hit by chance 19% of the time against 6.8% for one
    - so a lenient number is only readable next to that floor. Both are
    printed, with the floor, rather than one being chosen here.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import hashlib

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import config, retrieve                       # noqa: E402
from app.embed import embed                            # noqa: E402

TICKETS = ROOT / "benchmark" / "tickets.csv"
# Query vectors are the only paid part of a grid run, and they do not change
# between runs unless the queries do. Keyed by encoder and by a digest of the
# exact strings sent, so an edit to the ticket set invalidates it by itself.
QCACHE = ROOT / "data" / "kb" / "query_vectors"
RESULTS = ROOT / "eval" / "results"
TABLE = ROOT / "benchmark" / "results.csv"

VARIANTS = ["article", "section"]
ENCODERS = [
    "baai/bge-m3",
    "openai/text-embedding-3-small",
    "qwen/qwen3-embedding-8b",
]
KS = (1, 3, 5)
DEEP = 25          # chunks pulled before rolling up; 25 always yields 5 docs


def load_gold(path: Path) -> dict[str, list[str]]:
    """ticket id -> ordered document ids, empty list meaning no answer exists.

    Read from the `gold` column and not `proposed`, so that a row the engineer
    corrected is scored on his correction. They start out equal; the point of
    the column is that they stop being equal where he disagreed.
    """
    gold: dict[str, list[str]] = {}
    for row in csv.DictReader(path.open(encoding="utf-8-sig"), delimiter=";"):
        value = row["gold"].strip()
        gold[row["id"]] = [] if value in ("", "none") else value.split()
    return gold


def score(ranked: list[str], key: list[str]) -> dict:
    """One query against one key, at document level."""
    out: dict[str, float] = {}
    for k in KS:
        top = ranked[:k]
        out[f"lenient@{k}"] = float(any(d in top for d in key))
        out[f"strict@{k}"] = float(key[0] in top) if key else 0.0
    rank = next((i for i, d in enumerate(ranked[:5], start=1) if d in key), 0)
    out["mrr@5"] = 1.0 / rank if rank else 0.0
    out["rank"] = float(rank)
    return out


def rollup(hits: list[retrieve.Hit], want: int) -> tuple[list[str], int]:
    """First `want` distinct documents, and how many chunks that consumed."""
    docs: list[str] = []
    for used, hit in enumerate(hits, start=1):
        if hit.doc_id not in docs:
            docs.append(hit.doc_id)
        if len(docs) == want:
            return docs, used
    return docs, len(hits)


def cell(variant: str, method: str, encoder: str | None, rows: list[dict],
         gold: dict[str, list[str]], index: retrieve.Index,
         vectors: retrieve.Vectors | None,
         qvecs: dict[str, np.ndarray] | None) -> dict:
    per_query = []
    latencies = []
    chunk_costs = []
    for row in rows:
        key = gold.get(row["id"], [])
        if not key:
            continue          # abstention cases are scored separately
        started = time.perf_counter()
        hits = retrieve.search(row["original"], index, method, top=DEEP,
                               vectors=vectors,
                               query_vector=(qvecs or {}).get(row["id"]))
        latencies.append((time.perf_counter() - started) * 1000)
        ranked, used = rollup(hits, max(KS))
        chunk_costs.append(used)
        per_query.append({"id": row["id"], "lang": row["lang"],
                          "category": row["category"],
                          "store": row["store"],
                          "rail_uncertain": row["rail_uncertain"],
                          "returned": ranked,
                          # Chunk ids, not just documents: rail accuracy asks
                          # WHICH section of the cancellation article came
                          # back, and the rolled-up document id cannot say.
                          "chunks": [h.chunk_id for h in hits[:max(KS)]],
                          "top_score": round(float(hits[0].score), 5)
                          if hits else 0.0,
                          **score(ranked, key)})

    # The tickets the base cannot answer are not scored for recall - there is
    # nothing to recall - but their top score IS the measurement that sets the
    # abstention threshold, so it is taken here and kept apart.
    no_answer = []
    for row in rows:
        if row["id"] not in gold or gold[row["id"]]:
            continue
        hits = retrieve.search(row["original"], index, method, top=1,
                               vectors=vectors,
                               query_vector=(qvecs or {}).get(row["id"]))
        no_answer.append({"id": row["id"],
                          "top_score": round(float(hits[0].score), 5)
                          if hits else 0.0})

    keys = [f"{s}@{k}" for k in KS for s in ("lenient", "strict")] + ["mrr@5"]
    summary = {m: round(statistics.mean(q[m] for q in per_query), 4)
               for m in keys}
    return {
        "variant": variant, "method": method, "encoder": encoder or "",
        "queries": len(per_query),
        **summary,
        "chunks@5": round(statistics.mean(chunk_costs), 2),
        "p50_ms": round(statistics.median(latencies), 2),
        "per_query": per_query,
        "no_answer": no_answer,
    }


def chance_floor(gold: dict[str, list[str]], corpus: int, k: int) -> float:
    """What a random ranking would score, given how large the keys are."""
    import math
    hits = []
    for key in gold.values():
        if not key:
            continue
        g = min(len(key), corpus)
        hits.append(1 - math.comb(corpus - g, k) / math.comb(corpus, k))
    return round(statistics.mean(hits), 4)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="gold_gemini.csv")
    ap.add_argument("--translated", action="store_true",
                    help="stage 2: query with benchmark/tickets_en.json "
                         "instead of the text the customer wrote")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--encoders", nargs="*", default=ENCODERS)
    args = ap.parse_args()

    rows = list(csv.DictReader(TICKETS.open(encoding="utf-8-sig"),
                               delimiter=";"))
    if args.limit:
        rows = rows[:args.limit]
    if args.translated:
        # Substituted here rather than at search time so that EVERYTHING
        # downstream - the embedding, its cache key, the BM25 tokens - sees the
        # same string. A pipeline that translated for the encoder but not for
        # BM25 would be measuring a third design nobody proposed.
        english = json.loads(
            (ROOT / "benchmark" / "tickets_en.json").read_text(encoding="utf-8"))
        missing = [r["id"] for r in rows if r["id"] not in english]
        if missing:
            raise SystemExit(f"no translation for {len(missing)} tickets: "
                             f"re-run benchmark/translate.py")
        rows = [{**r, "original": english[r["id"]]} for r in rows]
    gold = load_gold(ROOT / "benchmark" / args.gold)
    answerable = [r for r in rows if gold.get(r["id"])]
    abstain = [r for r in rows if r["id"] in gold and not gold[r["id"]]]
    print(f"{len(rows)} tickets: {len(answerable)} with a key, "
          f"{len(abstain)} where the base has no answer")

    settings = config.load()
    # Embedded ONCE per encoder and reused across both chunkings and both
    # methods that need them: 3 x N calls rather than 14 x N.
    qvecs: dict[str, dict[str, np.ndarray]] = {}
    spent = 0.0
    texts = [r["original"] for r in rows]
    digest = hashlib.sha256("\x00".join(texts).encode("utf-8")).hexdigest()[:16]
    QCACHE.mkdir(parents=True, exist_ok=True)
    for encoder in args.encoders:
        path = QCACHE / f"{encoder.replace('/', '-')}__{digest}.npy"
        if path.exists():
            matrix = np.load(path)
            qvecs[encoder] = {r["id"]: matrix[i] for i, r in enumerate(rows)}
            print(f"  cached   {len(rows)} queries for {encoder}")
            continue
        started = time.perf_counter()
        result = embed(texts, encoder, settings)
        spent += result.cost_usd
        matrix = np.asarray(result.vectors, dtype=np.float32)
        np.save(path, matrix)
        qvecs[encoder] = {r["id"]: matrix[i] for i, r in enumerate(rows)}
        print(f"  embedded {len(rows)} queries with {encoder}: "
              f"{result.tokens} tokens, ${result.cost_usd:.5f}, "
              f"{time.perf_counter() - started:.1f}s")

    cells = []
    for variant in VARIANTS:
        index = retrieve.Index.load(variant)
        loaded = {e: retrieve.Vectors.load(variant, e, index)
                  for e in args.encoders}
        cells.append(cell(variant, "bm25", None, rows, gold, index, None, None))
        for encoder in args.encoders:
            for method in ("dense", "hybrid"):
                cells.append(cell(variant, method, encoder, rows, gold, index,
                                  loaded[encoder], qvecs[encoder]))
        print(f"  {variant}: {len(args.encoders) * 2 + 1} cells done")

    floors = {f"lenient@{k}": chance_floor(gold, 73, k) for k in KS}
    floors.update({f"strict@{k}": round(k / 73, 4) for k in KS})

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS.mkdir(parents=True, exist_ok=True)
    run = {
        "run": stamp,
        "gold": args.gold,
        "queries": len(answerable),
        "abstention_cases": len(abstain),
        "query_embedding_cost_usd": round(spent, 5),
        "chance_floor": floors,
        "index_fingerprints": {
            v: retrieve.Index.load(v).fingerprint for v in VARIANTS},
        "cells": cells,
    }
    out = RESULTS / f"retrieval_{stamp}.json"
    out.write_text(json.dumps(run, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")

    columns = ["variant", "method", "encoder", "queries"] + \
        [f"{s}@{k}" for k in KS for s in ("lenient", "strict")] + \
        ["mrr@5", "chunks@5", "p50_ms"]
    with TABLE.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter=";")
        writer.writeheader()
        for c in sorted(cells, key=lambda c: -c["lenient@5"]):
            writer.writerow({k: c[k] for k in columns})

    print(f"\nchance floor: lenient@5 {floors['lenient@5']:.1%}, "
          f"strict@5 {floors['strict@5']:.1%}")
    print(f"{'variant':<8} {'method':<7} {'encoder':<30} "
          f"{'len@1':>6} {'len@5':>6} {'str@5':>6} {'mrr':>6} "
          f"{'chunks':>7} {'ms':>6}")
    for c in sorted(cells, key=lambda c: -c["lenient@5"]):
        print(f"{c['variant']:<8} {c['method']:<7} {c['encoder']:<30} "
              f"{c['lenient@1']:>6.3f} {c['lenient@5']:>6.3f} "
              f"{c['strict@5']:>6.3f} {c['mrr@5']:>6.3f} "
              f"{c['chunks@5']:>7.1f} {c['p50_ms']:>6.1f}")
    print(f"\nrun  -> {out.relative_to(ROOT)}")
    print(f"table-> {TABLE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
