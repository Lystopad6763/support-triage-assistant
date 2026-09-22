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
PROMPTS = ROOT / "prompts" / "assist"
VERSION = "v2"

VARIANT = "article"
ENCODER = "openai/text-embedding-3-small"
MODEL = "google/gemini-3.1-flash-lite"
TOP_K = 5
TONES = ("formal", "empathetic", "concise")

# Sentence splitter for the check below. Crude on purpose: it only has to
# bound the window in which a negation counts, not to parse English.
SENTENCE = re.compile(r"(?<=[.!?])\s+")

# A reply that says "do NOT request a chargeback" is obeying pol-15, and the
# first version of this check flagged it as violating pol-15 - three times out
# of twenty, every one of them a correct warning. It matched the TOPIC, not the
# CLAIM. A check that lights up on correct behaviour is worse than no check,
# because within a week nobody reads it.
#
# So a match only counts when its own sentence does not negate or discourage
# it. This is not sentiment analysis; it is the difference between "you can
# request a chargeback" and "please do not request a chargeback", and that
# difference is carried by a small closed set of words.
NEGATION = re.compile(
    r"\b(not|n't|never|cannot|unable|avoid|refrain|instead of|rather than|"
    r"do not|does not|will not|won't|unfortunately)\b", re.I)
# The negation has to be NEAR the thing it negates. Skipping any sentence that
# contained a negative let "we recommend a chargeback if we have not replied in
# a week" through: the "not" belongs to the other clause entirely. Sixty
# characters is about one clause of English.
NEGATION_WINDOW = 60
# A reply that repeats a customer's mistaken belief in order to correct it is
# not asserting it. This is the frame that marks the repetition as reported
# rather than claimed, and an empathetic reply reaches for it constantly -
# naming what the person expected is most of what "empathetic" means here.
REPORTED = re.compile(
    r"\b(you (believed|thought|expected|assumed|may have (believed|thought|"
    r"expected|assumed))|it sounds like|many (people|users) (assume|think|"
    r"believe)|some (people|users) (assume|think|believe)|the assumption)\b",
    re.I)


def violations(text: str) -> list[str]:
    """Which of the seven prohibitions this text actually commits.

    Used by the assistant on every draft and by eval/guards.py on a fixed list
    of phrasings that must and must not fire - one implementation, so a guard
    cannot pass its test and behave differently in production.
    """
    found: list[str] = []
    for part in SENTENCE.split(text):
        for name, pattern, source in BANNED:
            match = pattern.search(part)
            if not match:
                continue
            before = part[max(0, match.start() - NEGATION_WINDOW):
                          match.start()]
            if NEGATION.search(before) or NEGATION.search(match.group(0)):
                continue
            # Looking forward as well was tried and abandoned. It excused the
            # empathetic shape correctly - "you believed uninstalling the app
            # would end your trial, but that does not cancel it" - and in the
            # same move excused a real one, "we recommend a chargeback if we
            # have not replied in a week", where the negation belongs to
            # another clause entirely. Both have their negation downstream, so
            # position cannot separate them.
            #
            # What separates them is that one REPORTS a belief in order to
            # correct it. That is a verb, and a short list of them, and it is
            # the thing actually being detected.
            if REPORTED.search(part[:match.start()]):
                continue
            label = f"{name} ({source})"
            if label not in found:
                found.append(label)
    return found

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
    # SHORT is the violation, not "a number of days". The first version of this
    # pattern flagged "a confirmed refund takes at least 15 business days" -
    # which is pol-14's own sentence, so the check was calling the policy a
    # breach of itself. The number has to be under fifteen, or vague in the way
    # a hurried promise is vague.
    ("promises a short refund window",
     re.compile(r"refund[^.]{0,40}\b(a few|couple|[1-9]|1[0-4])\s*"
                r"(business\s+)?(day|days|hours)\b", re.I), "pol-14"),
    # Matching the word "chargeback" flagged three correct warnings out of
    # twenty. Adding negation-awareness left one: "please be advised that
    # initiating a chargeback may result in the immediate termination of your
    # account" discourages it without a single negative word, and my frame
    # accepted "please" as if it were a recommendation.
    #
    # pol-15 forbids RECOMMENDING one. So the pattern needs a recommending
    # frame - a second person modal, an explicit recommendation, or the
    # sentence opening with the imperative - and "please be advised" is none of
    # the three.
    ("suggests a chargeback",
     re.compile(r"(you (can|could|should|may|might)|we (recommend|suggest|"
                r"advise)|feel free to|consider|^\s*(file|request|initiate|"
                r"start|open)\b)[^.]{0,40}"
                r"\b(chargeback|dispute (it|the charge|this) with your bank)\b",
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

    def __init__(self, settings=None, model: str = MODEL,
                 version: str = VERSION):
        self.settings = settings or config.load()
        self.model = model
        self.version = version
        self.index = retrieve.Index.load(VARIANT)
        self.vectors = retrieve.Vectors.load(VARIANT, ENCODER, self.index)
        self.system = (PROMPTS / f"{version}.md").read_text(encoding="utf-8")
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
            version=f"assist/{self.version}", model=self.model,
            temperature=0.3,
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

        out.banned = []
        for tone in TONES:
            for label in violations(getattr(o, tone)):
                if label not in out.banned:
                    out.banned.append(label)

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


def draft(ticket: str, settings=None, model: str = MODEL,
          version: str = VERSION) -> Result:
    global _engine
    if (_engine is None or _engine.model != model
            or _engine.version != version):
        _engine = Engine(settings, model, version)
    return _engine.draft(ticket)
