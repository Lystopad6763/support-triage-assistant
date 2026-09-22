"""Build the searchable index over the knowledge base, and its vectors.

    Run: python scripts/build_kb.py            both variants, all three encoders
         python scripts/build_kb.py --dry-run  sizes and cost, no API calls

WHAT IT WRITES
    data/kb/index.json                    the chunks themselves, both variants
    data/kb/vectors__<variant>__<enc>.json  one file per (variant, encoder)

TWO VARIANTS, BECAUSE THE CHUNKING DECISION IS MEASURED AND NOT ASSUMED
    article  84 chunks, one per document. Every document already sits inside the
             256-1024 token band the course names for a semantic chunk (median
             227, max 868), so there is nothing to cut.
    section  99 chunks. Eight documents carry their own internal headings; the
             one that matters is "How to cancel subscription?", whose six
             sections are the six PURCHASE RAILS, and the rail decides routing -
             an App Store refund is Apple's decision, Google Play and web are
             ours. One vector for all six rails is the blur this variant exists
             to measure.
    The eval picks the winner and it is then frozen: the course rule is that a
    chunking strategy is not changed after indexing, because every recall number
    measured before the change silently stops being comparable.

THE FINGERPRINT
    Every vector file records a sha256 over the chunk ids and their text. An
    index built against a knowledge base that has since been re-collected is the
    classic stale-RAG failure - the documents change, the vectors do not, and
    nothing errors. Here the retriever refuses to load a mismatched pair.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import kb                              # noqa: E402
from app.config import load                     # noqa: E402
from app.embed import DIMENSIONS, embed         # noqa: E402

OUT = ROOT / "data" / "kb"


def chunks(variant: str) -> list[dict]:
    # verify() checks the whole collection; indexed() drops what was judged
    # unable to answer any ticket - see kb.EXCLUDED for the list and why.
    docs = kb.indexed(kb.verify())
    if variant == "article":
        return [dict(meta(doc), id=doc.id, heading="", anchor="",
                     text=doc.text, tokens_est=doc.tokens_est)
                for doc in docs]

    # Deduplication spans the corpus, so the sections come back as one list
    # rather than per document - see kb.sections().
    parents = {doc.id: doc for doc in docs}
    reachable = {section.doc_id for section in kb.sections(docs)}
    orphaned = sorted(doc.id for doc in docs if doc.id not in reachable)
    if orphaned:
        raise SystemExit(
            "indexed but unreachable in this variant, so retrieval can never "
            "return them: " + ", ".join(orphaned))
    return [dict(meta(parents[section.doc_id]), id=section.id,
                 heading=section.heading, anchor=section.anchor,
                 url=section.url, text=section.text,
                 tokens_est=section.tokens_est)
            for section in kb.sections(docs)]


def meta(doc: kb.Doc) -> dict:
    """The payload the retriever hands back with every hit.

    The course calls for source, date, language and document version alongside
    the text, and each field here answers a question the assistant or the agent
    actually asks:

        updated_at    when the company last edited it. Stale answers are the
                      named failure of a RAG system whose documents move and
                      whose vectors do not - "How to cancel subscription?" was
                      edited on 2026-09-21, four days after this project began.
        lang          "en" for all 74, and that is the finding, not a default:
                      the help centre serves one locale, so every non-English
                      ticket - 51.6% of the set - is a cross-lingual lookup.
        url_status    "verified" on the 19 policies, meaning the address was
                      opened and checked. A citation the agent forwards to a
                      customer carries a different weight when it is verified.
        url_is_page   whether the link opens this document or the page holding
                      it (the 9 FAQ entries share one address).

    None of it is embedded. The vector is built from the title, the breadcrumb
    and the body only: a date in the embedded text would push every chunk of
    the same vintage together and measure nothing.
    """
    return {
        "doc_id": doc.id,
        "source": doc.source,
        "title": doc.title,
        "category": doc.category,
        "section": doc.section,
        "url": doc.url,
        "url_is_page": doc.url_is_page,
        "url_status": doc.url_status,
        "updated_at": doc.updated_at,
        "lang": "en",
    }


def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(row["id"].encode("utf-8"))
        digest.update(b"\x00")
        digest.update(row["text"].encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


def pack(vectors: list[list[float]]) -> str:
    """float32, little-endian, base64.

    JSON floats would be five times the size and would still not be exact. This
    is not a binary format anyone has to reverse-engineer: it is struct + b64,
    unpacked in three lines by the retriever.
    """
    flat = [value for vector in vectors for value in vector]
    return base64.b64encode(struct.pack(f"<{len(flat)}f", *flat)).decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=["article", "section", "both"],
                        default="both")
    parser.add_argument("--models", nargs="*", default=list(DIMENSIONS))
    parser.add_argument("--dry-run", action="store_true",
                        help="report sizes and predicted cost, call nothing")
    args = parser.parse_args()

    variants = ["article", "section"] if args.variant == "both" else [args.variant]
    settings = load()
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    index = {"built_at": now, "variants": {}}
    for variant in variants:
        rows = chunks(variant)
        index["variants"][variant] = {
            "fingerprint": fingerprint(rows),
            "chunks": rows,
            "tokens_est": sum(r["tokens_est"] for r in rows),
        }
        print(f"{variant:<8} {len(rows):>3} chunks, "
              f"{sum(r['tokens_est'] for r in rows):>6} est tokens, "
              f"fingerprint {index['variants'][variant]['fingerprint'][:16]}")

    if args.dry_run:
        for variant in variants:
            rows = index["variants"][variant]["chunks"]
            for model in args.models:
                dims = DIMENSIONS.get(model, 0)
                size = len(rows) * dims * 4 / 1024
                print(f"  would embed {variant:<8} on {model:<32} "
                      f"-> {len(rows)}x{dims}, {size:>7.0f} KB packed")
        return

    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote data/kb/index.json "
          f"({(OUT / 'index.json').stat().st_size / 1024:.0f} KB)")

    total_cost = 0.0
    print(f"\n{'variant':<8} {'encoder':<32} {'dims':>5} {'tokens':>7} "
          f"{'$':>9} {'s':>6} {'file KB':>8}")
    for variant in variants:
        rows = index["variants"][variant]["chunks"]
        for model in args.models:
            result = embed([r["text"] for r in rows], model, settings)
            total_cost += result.cost_usd
            path = OUT / f"vectors__{variant}__{model.replace('/', '-')}.json"
            path.write_text(json.dumps({
                "model": model,
                "variant": variant,
                "dims": result.dims,
                "count": len(rows),
                "built_at": now,
                "fingerprint": index["variants"][variant]["fingerprint"],
                "tokens": result.tokens,
                "cost_usd": result.cost_usd,
                "ids": [r["id"] for r in rows],
                "vectors_b64": pack(result.vectors),
            }, ensure_ascii=False), encoding="utf-8")
            print(f"{variant:<8} {model:<32} {result.dims:>5} "
                  f"{result.tokens:>7} {result.cost_usd:>9.5f} "
                  f"{result.latency_ms / 1000:>6.1f} "
                  f"{path.stat().st_size / 1024:>8.0f}")

    print(f"\ntotal embedding cost: ${total_cost:.5f}")


if __name__ == "__main__":
    main()
