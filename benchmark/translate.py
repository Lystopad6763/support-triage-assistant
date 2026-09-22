"""Translate the non-English tickets into English, for stage 2 of the benchmark.

    python benchmark/translate.py

WHAT STAGE 2 ASKS
    The knowledge base is English. 208 of the 430 tickets are not. Stage 1
    measured how well three encoders cross that gap by themselves; this asks
    whether translating the query first crosses it better.

    It is a real question and not a formality: a translation step costs a model
    call on every ticket, adds a second or two of latency, and introduces a
    second thing that can be wrong. It has to earn that.

    The answer may well be no - a multilingual encoder aligns languages inside
    one vector space, which is exactly the job, while a translator can drop the
    one word the retrieval needed. A negative result is reported, not buried.

ONLY THE NON-ENGLISH ONES ARE TRANSLATED
    The English tickets are carried through unchanged. Sending them through a
    translator too would measure the translator's willingness to leave text
    alone, which is not the question, and would move the English numbers for a
    reason having nothing to do with language.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import config, llm                            # noqa: E402

HERE = Path(__file__).resolve().parent
TICKETS = HERE / "tickets.csv"
OUT = HERE / "tickets_en.json"
PROMPT = ROOT / "prompts" / "translate" / "v1.md"

MODEL = "google/gemini-3.1-flash-lite"
WORKERS = 8
ENGLISH = {"en_or_unknown"}


class Translation(BaseModel):
    english: str


SCHEMA = {
    "name": "translation",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["english"],
        "properties": {"english": {"type": "string"}},
    },
}


def one(row: dict, system: str, prompt, settings) -> dict:
    result = llm.Result(ticket_id=row["id"], model=prompt.model)
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": row["original"]}]
    started = time.monotonic()
    out = llm.run(messages, result, prompt, settings,
                  schema=SCHEMA, model_cls=Translation)
    return {
        "id": row["id"],
        "lang": row["lang"],
        "english": out.english if out else row["original"],
        "failed": out is None,
        "cost_usd": getattr(result, "cost_usd", 0.0),
        "latency_ms": int((time.monotonic() - started) * 1000),
    }


def main() -> None:
    rows = list(csv.DictReader(TICKETS.open(encoding="utf-8-sig"),
                               delimiter=";"))
    todo = [r for r in rows if r["lang"] not in ENGLISH and r["original"].strip()]
    settings = config.load()
    system = PROMPT.read_text(encoding="utf-8")
    prompt = config.PromptConfig(
        version="translate/v1", model=MODEL, temperature=0.0,
        response_format="json_schema", text_override=system,
        tested_on="stage 2 of the retrieval benchmark",
        change_reason="first version")

    print(f"{len(todo)} non-English tickets of {len(rows)}")
    done = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for got in pool.map(lambda r: one(r, system, prompt, settings), todo):
            done.append(got)
            if len(done) % 50 == 0:
                print(f"  {len(done)}/{len(todo)}  "
                      f"${sum(d['cost_usd'] for d in done):.4f}", flush=True)

    # English tickets travel through as themselves, so the output is a complete
    # query set and the caller never has to remember which half to substitute.
    by_id = {d["id"]: d["english"] for d in done}
    payload = {r["id"]: by_id.get(r["id"], r["original"]) for r in rows}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                   encoding="utf-8")

    failed = [d["id"] for d in done if d["failed"]]
    cost = sum(d["cost_usd"] for d in done)
    latency = sorted(d["latency_ms"] for d in done)
    print(f"\n{len(done)} translated, ${cost:.4f}, "
          f"median {latency[len(latency) // 2]} ms")
    print(f"  failed (left in the original): {len(failed)}")
    print(f"  -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
