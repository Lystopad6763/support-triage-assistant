"""An exact-match cache for triage results, keyed by everything that decides them.

WHY A CACHE AT ALL
    Support traffic repeats itself. In this corpus 1,192 ticket-shaped rows carry
    only 1,147 distinct texts, and that is public reviews, where people write
    once. A real queue has retries, duplicate submissions, the same person
    writing twice, and re-runs of the same batch after a crash. Every one of
    those is a call we have already paid for.

    The saving is not the interesting part, though. Determinism is. temperature 0
    does not give the same answer twice here - six runs of one prompt spread over
    68-80% - so a ticket re-opened by an agent can show a different priority than
    the one they saw an hour ago. A cache makes the system's answer to a given
    ticket stable for as long as the prompt stays the same, which is the
    behaviour a support team expects.

WHAT THE KEY CONTAINS, AND WHY THAT IS THE INVALIDATION RULE
    sha256 of: the RENDERED prompt, the model, the temperature, the response
    format, the reasoning effort, and the ticket text.

    There is no TTL and there is no manual flush, because there is nothing to
    expire: a cached answer is only ever served to a request that would have
    produced it. Edit one word of the prompt, bump the version, swap the model,
    change temperature - the hash moves and every old entry becomes unreachable.
    That is invalidation by construction rather than by remembering to do it.

    Note what is NOT in the key: the ticket id. Two different tickets with
    identical text get the same answer, which is correct and is also where most
    of the real-world hits come from.

WHAT IT MUST NOT BE USED FOR
    Measuring run-to-run variance, and benchmarking. Both need fresh calls -
    a cached run would report a spread of zero and a cost of zero, which is true
    and useless. So it is off by default and turned on explicitly.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Entry:
    triage: dict
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int


class Cache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS triage ("
            " key TEXT PRIMARY KEY,"
            " prompt_sha TEXT, model TEXT, text_sha TEXT,"
            " payload TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        self.db.commit()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(prompt_sha: str, model: str, temperature: float,
            response_format: str, reasoning_effort: str | None, text: str) -> str:
        blob = "\x1f".join([prompt_sha, model, f"{temperature:.3f}",
                            response_format, reasoning_effort or "-", text])
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Entry | None:
        row = self.db.execute(
            "SELECT payload FROM triage WHERE key = ?", (key,)).fetchone()
        if not row:
            self.misses += 1
            return None
        self.hits += 1
        data = json.loads(row[0])
        return Entry(**data)

    def put(self, key: str, prompt_sha: str, model: str, text: str,
            entry: Entry) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO triage "
            "(key, prompt_sha, model, text_sha, payload) VALUES (?, ?, ?, ?, ?)",
            (key, prompt_sha, model,
             hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
             json.dumps(entry.__dict__, ensure_ascii=False)))
        self.db.commit()

    def stats(self) -> dict:
        total = self.hits + self.misses
        rows = self.db.execute("SELECT COUNT(*) FROM triage").fetchone()[0]
        return {"hits": self.hits, "misses": self.misses,
                "hit_rate": self.hits / total if total else 0.0,
                "stored": rows}
