"""One ticket in, material for a human agent out.

    from app import assist
    result = assist.draft(ticket_text, settings)

WHAT THE MEASUREMENT CHOSE
    eval/retrieval.py scored fourteen designs on 430 hand-labelled tickets, and
    this module is the winner, unchanged: the article index, dense retrieval,
    text-embedding-3-small, top five documents, the customer's own text as the
    query.

    Three things were measured and rejected, and they are not here for reasons,
    not for lack of time:

        hybrid BM25 + dense lost to dense alone in all six pairings, and lost
        worst on the non-English half - BM25 scored 0.000 on Turkish, and RRF
        weights it equally with a retriever that scored 0.857.

        translating the ticket first gained 1.7 points on the winner, which is
        9 tickets fixed against 2 broken out of 200 - p = 0.065, not a result -
        for 1.8 seconds on every ticket and one more thing to fail.

        the section index returns a confidently WRONG cancellation rail: each
        encoder locks onto one of the six sections by style, 8% to 33% correct
        against a 17% chance floor. The article carries all six rails, so the
        agent reads the right one.

WHY THE CHECKS BELOW RUN ON EVERY DRAFT
    The prompt forbids seven things, each one a promise this company cannot
    keep. A prompt is a request, not a guarantee, so the same seven are checked
    mechanically afterwards. A draft that trips one is flagged and shown to the
    agent flagged - never silently dropped, because the agent has to see what
    the assistant tried to say.
"""
from __future__ import annotations

import difflib
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from app import config, llm, retrieve
from app.embed import embed

ROOT = Path(__file__).resolve().parent.parent
PROMPT = ROOT / "prompts" / "assist" / "v1.md"

VARIANT = "article"
ENCODER = "openai/text-embedding-3-small"
MODEL = "google/gemini-3.1-flash-lite"
TOP_K = 5
TONES = ("formal", "empathetic", "concise")

# Each pattern is one of the seven prohibitions in the prompt, with the
# document that makes it a prohibition. They are deliberately narrow: a check
# that fires on the word "refund" would fire on every correct reply and would
# be switched off within a day.
BANNED: list[tuple[str, re.Pattern, str]] = [
    ("promises an App Store refund",
     re.compile(r"\bwe (will|'ll) (issue|process|send|give)[^.]{0,40}refund"
                r"[^.]{0,60}(app ?store|apple|itunes)", re.I), "pol-04"),
    ("promises credits back",
     re.compile(r"refund[^.]{0,30}\b(credits?|balance|units?)\b", re.I),
     "pol-05"),
    ("promises a short refund window",
     re.compile(r"refund[^.]{0,40}\b(\d{1,2}|a few|couple)\s*"
                r"(business\s+)?(day|days|hours)\b", re.I), "pol-14"),
    ("suggests a chargeback",
     re.compile(r"\b(chargeback|dispute (it|the charge) with your bank)\b",
                re.I), "pol-15"),
    ("says deleting the app cancels",
     re.compile(r"(delete|uninstall|remove)[^.]{0,40}(app)[^.]{0,40}"
                r"(cancel|stop|end)", re.I), "pol-04, pol-16"),
    ("decides refund entitlement",
     re.compile(r"\byou (are|'re) (entitled|eligible) (to|for) a refund\b",
                re.I), "pol-14"),
    ("claims advisors are screened",
     re.compile(r"\b(advisors?|psychics?|experts?)[^.]{0,40}"
                r"\b(screened|vetted|verified|background[- ]check)", re.I),
     "pol-11"),
]


class Output(BaseModel):
    summary: str
    grounded: bool
    citation_doc_id: str
    citation_quote: str
    formal: str
    empathetic: str
    concise: str
    needs_human: bool
    needs_human_reason: str


SCHEMA = {
    "name": "agent_assist",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["summary", "grounded", "citation_doc_id",
                     "citation_quote", "formal", "empathetic", "concise",
                     "needs_human", "needs_human_reason"],
        "properties": {
            "summary": {"type": "string"},
            "grounded": {"type": "boolean"},
            "citation_doc_id": {"type": "string"},
            "citation_quote": {"type": "string"},
            "formal": {"type": "string"},
            "empathetic": {"type": "string"},
            "concise": {"type": "string"},
            "needs_human": {"type": "boolean"},
            "needs_human_reason": {"type": "string"},
        },
    },
}

SPACE = re.compile(r"\s+")


def flat(text: str) -> str:
    return SPACE.sub(" ", text).strip().lower()


@dataclass
class Source:
    doc_id: str
    title: str
    url: str
    url_is_page: bool
    text: str
    rank: int


@dataclass
class Result:
    ticket: str
    output: Output | None
    sources: list[Source] = field(default_factory=list)
    citation_ok: bool = False
    citation_url: str = ""
    banned: list[str] = field(default_factory=list)
    similarity: dict[str, float] = field(default_factory=dict)
    error: str = ""
    retrieval_ms: int = 0
    generation_ms: int = 0
    embed_cost_usd: float = 0.0
    generation_cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        return self.embed_cost_usd + self.generation_cost_usd

    @property
    def total_ms(self) -> int:
        return self.retrieval_ms + self.generation_ms


class Engine:
    """Index, vectors and prompt, loaded once and reused.

    Built as an object rather than module globals so that a web process loads
    the 400 KB of vectors at startup and not on the first person's request.
    """

    def __init__(self, settings=None, model: str = MODEL):
        self.settings = settings or config.load()
        self.model = model
        self.index = retrieve.Index.load(VARIANT)
        self.vectors = retrieve.Vectors.load(VARIANT, ENCODER, self.index)
        self.system = PROMPT.read_text(encoding="utf-8")
        self.by_doc = {c["doc_id"]: c for c in self.index.chunks}

    def find(self, ticket: str) -> tuple[list[Source], float]:
        result = embed([ticket], ENCODER, self.settings)
        vector = np.asarray(result.vectors[0], dtype=np.float32)
        hits = retrieve.search(ticket, self.index, "dense", top=TOP_K,
                               vectors=self.vectors, query_vector=vector)
        return [Source(h.doc_id, h.title, h.url, h.url_is_page, h.text, h.rank)
                for h in hits], result.cost_usd

    def render(self, ticket: str, sources: list[Source]) -> str:
        blocks = [f"[{s.doc_id}] {s.title}\n{s.text}" for s in sources]
        return ("KNOWLEDGE BASE - the only facts you have\n\n"
                + "\n\n---\n\n".join(blocks)
                + "\n\n=== TICKET ===\n\n" + ticket)

    def draft(self, ticket: str) -> Result:
        out = Result(ticket=ticket, output=None)
        started = time.monotonic()
        out.sources, out.embed_cost_usd = self.find(ticket)
        out.retrieval_ms = int((time.monotonic() - started) * 1000)

        prompt = config.PromptConfig(
            version="assist/v1", model=self.model, temperature=0.3,
            response_format="json_schema",
            text_override=self.system,
            tested_on="benchmark/tickets.csv",
            change_reason="first version of the agent-assist prompt")
        record = llm.Result(ticket_id="", model=self.model)
        messages = [{"role": "system", "content": self.system},
                    {"role": "user",
                     "content": self.render(ticket, out.sources)}]
        started = time.monotonic()
        out.output = llm.run(messages, record, prompt, self.settings,
                             schema=SCHEMA, model_cls=Output)
        out.generation_ms = int((time.monotonic() - started) * 1000)
        out.error = record.error or ""
        out.generation_cost_usd = getattr(record, "cost_usd", 0.0)
        out.input_tokens = record.input_tokens
        out.output_tokens = record.output_tokens
        if out.output is not None:
            self.check(out)
        return out

    def check(self, out: Result) -> None:
        """Everything that can be verified without a human, verified."""
        o = out.output
        assert o is not None

        # The quote has to exist in the document it names, and that document
        # has to be one retrieval actually returned - otherwise the agent
        # clicks a link to a page that does not contain the sentence.
        chunk = self.by_doc.get(o.citation_doc_id)
        retrieved = {s.doc_id for s in out.sources}
        out.citation_ok = bool(
            o.citation_quote and chunk
            and o.citation_doc_id in retrieved
            and flat(o.citation_quote) in flat(chunk["text"]))
        out.citation_url = chunk["url"] if chunk else ""

        body = " ".join(getattr(o, tone) for tone in TONES)
        out.banned = [f"{name} ({source})"
                      for name, pattern, source in BANNED
                      if pattern.search(body)]

        # Tone variation is the thing most likely to be fake here: one reply
        # rewritten three times reads like three until it is measured. The
        # number goes to the agent and to the report, because the assignment
        # asks for the failures of tone variation and not only the method.
        for a, b in (("formal", "empathetic"), ("formal", "concise"),
                     ("empathetic", "concise")):
            ratio = difflib.SequenceMatcher(
                None, flat(getattr(o, a)), flat(getattr(o, b))).ratio()
            out.similarity[f"{a}~{b}"] = round(ratio, 3)


_engine: Engine | None = None


def draft(ticket: str, settings=None, model: str = MODEL) -> Result:
    global _engine
    if _engine is None or (settings is not None and _engine.settings is not settings):
        _engine = Engine(settings, model)
    return _engine.draft(ticket)
