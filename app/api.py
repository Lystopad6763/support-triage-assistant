"""The web form the assignment asks for, and the four things that keep it up.

    uvicorn app.api:app --reload          # locally
    uvicorn app.api:app --host 0.0.0.0 --port 8080

WHAT IT SERVES
    One page. Paste a ticket, get the summary an agent needs, three replies in
    shapes that differ on purpose, and one sentence quoted from the document it
    came from with a link to it.

WHY THERE ARE LIMITS ON A DEMO
    This is meant to stay up for a week while people who have never seen it
    try things. Every request spends real money at a provider, so the failure
    that matters is not a crash - it is a page that answers for two days and
    then quietly cannot, because the balance is gone and nobody was watching.

        length      12,000 characters, which is the longest ticket in the whole
                    430 and about 4,000 tokens. Past that the request is
                    refused rather than truncated: a silently truncated ticket
                    produces a confident answer to half a complaint.
        per address roughly one request every four seconds, burst of five. Slow
                    enough to stop a loop, fast enough that nobody testing by
                    hand ever meets it.
        per day     a hard ceiling on spend. When it is reached the page says
                    so plainly instead of erroring, because "we are out of
                    budget" and "it is broken" should not look the same.

    The key never leaves the server. The page talks to this process and this
    process talks to the provider, which is the only arrangement where the key
    is not in a browser.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import assist, config, llm, taxonomy

ROOT = Path(__file__).resolve().parent.parent
# The built React app. It is committed rather than built at deploy time, so the
# production image needs Python and nothing else - no node, no npm install
# reaching the network while a machine is trying to come up.
DIST = ROOT / "web" / "dist"

MAX_CHARS = 12_000
RATE_WINDOW = 20.0          # seconds
RATE_BURST = 5              # requests allowed inside one window
DAILY_BUDGET_USD = 5.00

app = FastAPI(title="Nebula agent assist", docs_url=None, redoc_url=None)

_engine: assist.Engine | None = None
_settings: config.Settings | None = None
_seen: dict[str, deque] = defaultdict(deque)
_spent: dict[str, float] = defaultdict(float)


class Ask(BaseModel):
    ticket: str = Field(min_length=1, max_length=MAX_CHARS)


@app.on_event("startup")
def warm() -> None:
    """Load the index and the vectors now, not on the first person's request.

    It is about 900 KB and a second of work. Doing it lazily means exactly one
    visitor - usually the first one, often the one being shown the demo - waits
    for it on top of everything else.
    """
    global _engine, _settings
    _engine = assist.Engine(config.load())
    _settings = config.load()


def allowed(client: str) -> bool:
    now = time.monotonic()
    hits = _seen[client]
    while hits and now - hits[0] > RATE_WINDOW:
        hits.popleft()
    if len(hits) >= RATE_BURST:
        return False
    hits.append(now)
    return True


@app.get("/")
def page() -> FileResponse:
    return FileResponse(DIST / "index.html")


@app.get("/health")
def health() -> dict:
    today = date.today().isoformat()
    return {
        "ok": _engine is not None,
        "model": _engine.model if _engine else None,
        "prompt": f"assist/{_engine.version}" if _engine else None,
        "encoder": assist.ENCODER,
        "chunks": len(_engine.index.chunks) if _engine else 0,
        "fingerprint": _engine.index.fingerprint[:16] if _engine else "",
        "spent_today_usd": round(_spent[today], 4),
        "daily_budget_usd": DAILY_BUDGET_USD,
    }


@app.post("/draft")
def draft(ask: Ask, request: Request) -> JSONResponse:
    today = date.today().isoformat()
    if _spent[today] >= DAILY_BUDGET_USD:
        return JSONResponse(status_code=429, content={
            "error": "budget",
            "message": "Денний бюджет демонстрації вичерпано. "
                       "Спробуйте завтра."})

    client = request.client.host if request.client else "unknown"
    if not allowed(client):
        return JSONResponse(status_code=429, content={
            "error": "rate",
            "message": "Забагато запитів поспіль. Зачекайте кілька секунд."})

    assert _engine is not None
    result = _engine.draft(ask.ticket.strip())
    _spent[today] += result.cost_usd

    # Crisis stops everything before a model is asked anything, so this returns
    # a different shape entirely: no summary, no citation, no drafts. The page
    # is expected to render the hotlines and nothing else.
    b = result.boundary
    if b is not None and b.halts:
        return JSONResponse(content={
            "halted": "crisis",
            "matched": b.matched.get("crisis", []),
            "resources": b.resources,
            "resources_url": b.resources_url,
        })

    if result.output is None:
        return JSONResponse(status_code=502, content={
            "error": "model",
            "message": result.error or "Модель не повернула відповідь."})

    o = result.output
    return JSONResponse(content={
        # What they are answered in, which is what the page labels the drafts
        # with. Russian tickets are answered in Ukrainian, so the two differ
        # there and the page says so rather than quietly substituting.
        "language": result.reply_language,
        "detected_language": result.detected_language,
        "summary": o.summary,
        "grounded": o.grounded,
        "needs_human": o.needs_human,
        "needs_human_reason": o.needs_human_reason,
        "banned": result.banned,
        # The deterministic pre-pass, reported next to the model's own
        # needs_human so the agent can see which noticed. Either is enough.
        "boundaries": {
            "flags": b.flags if b else [],
            "matched": b.matched if b else {},
        },
        "citation": {
            "doc_id": o.citation_doc_id,
            "quote": o.citation_quote,
            "url": result.citation_url,
            "verified": result.citation_ok,
            "is_page": next((s.url_is_page for s in result.sources
                             if s.doc_id == o.citation_doc_id), False),
        },
        "replies": [{
            "tone": tone,
            "english": getattr(o, tone),
            "localised": result.localised.get(tone, ""),
        } for tone in assist.TONES],
        "sources": [{"doc_id": s.doc_id, "title": s.title, "url": s.url,
                     "is_page": s.url_is_page} for s in result.sources],
        "similarity": result.similarity,
        "meta": {
            "model": _engine.model,
            "prompt": f"assist/{_engine.version}",
            "retrieval_ms": result.retrieval_ms,
            "generation_ms": result.generation_ms,
            "localise_ms": result.localise_ms,
            "total_ms": result.total_ms,
            "cost_usd": round(result.cost_usd, 6),
        },
    })


@app.get("/taxonomy")
def vocabulary() -> dict:
    """The label vocabulary, for the cheat sheet beside the classifier.

    Served rather than written into the page, because app/taxonomy.py is the
    single place the vocabulary is spelled out and a second copy in JSX would
    drift from it the first time a definition was sharpened. Free: no model is
    called, so it needs neither the budget nor the rate limit.

    The definitions go out in English, which is the language the model is given
    them in. A translated cheat sheet would describe the rules; this one IS the
    rules, word for word, and that difference is the whole point of showing it
    next to an answer the reader is trying to check.
    """
    hard = {f.value for f in taxonomy.HARD_FACTS}
    return {
        # Declaration order is the test order and the sheet must preserve it:
        # several tickets satisfy two tests at once and the first one wins.
        "categories": [{
            "code": c.value,
            "share": taxonomy.CATEGORY_GUIDE[c]["share"],
            "test": taxonomy.CATEGORY_GUIDE[c]["test"],
            "not": taxonomy.CATEGORY_GUIDE[c]["not"],
            "steps": [s.value for s in taxonomy.ALLOWED[c]],
        } for c in taxonomy.Category],
        "facts": [{"code": code, "definition": text,
                   "hard": code in hard}
                  for code, text in taxonomy.PRIORITY_FACTS],
        "priority_rule": taxonomy.PRIORITY_RULE,
        "steps": [{"code": s.value, "guide": taxonomy.STEP_GUIDE[s]}
                  for s in taxonomy.NextStep],
        "review_rules": [{"code": code, "why": why}
                         for code, why in taxonomy.REVIEW_RULES],
    }


@app.post("/classify")
def classify(ask: Ask, request: Request) -> JSONResponse:
    """Task 1 through the same page: one ticket in, three labels out.

    It shares the budget and the rate limit with /draft rather than having its
    own, because both spend from the same balance and a demo that runs out on
    one endpoint while the other keeps going is a confusing thing to watch.

    The answer carries its own audit next to it: whether the quoted span is
    really in the ticket, whether the priority follows from the fact list the
    model itself wrote, whether the next step is one the table allows for the
    category. Those three are checked here, deterministically, and they are the
    same checks eval/run.py counts over the whole set - so what the page shows
    for one ticket is the same measurement the report quotes for 157.
    """
    today = date.today().isoformat()
    if _spent[today] >= DAILY_BUDGET_USD:
        return JSONResponse(status_code=429, content={
            "error": "budget",
            "message": "Денний бюджет демонстрації вичерпано. "
                       "Спробуйте завтра."})

    client = request.client.host if request.client else "unknown"
    if not allowed(client):
        return JSONResponse(status_code=429, content={
            "error": "rate",
            "message": "Забагато запитів поспіль. Зачекайте кілька секунд."})

    assert _settings is not None
    text = ask.ticket.strip()
    prompt = config.PROMPTS[config.CLASSIFIER_PROMPT]
    result = llm.classify({"ticket_id": "web", "text": text}, _settings,
                          model=config.CLASSIFIER_MODEL, prompt=prompt)
    _spent[today] += result.cost_usd

    t = result.triage
    if t is None:
        return JSONResponse(status_code=502, content={
            "error": "model",
            "message": result.error or "Модель не повернула відповідь."})

    evidence = (t.evidence or "").strip()
    flags = taxonomy.review_flags(t, text)
    return JSONResponse(content={
        "category": t.category.value,
        "secondary_categories": [c.value for c in (t.secondary_categories or [])],
        "priority": t.priority.value,
        "priority_facts": [getattr(f, "value", f)
                           for f in (t.priority_facts or [])],
        "next_step": t.next_step.value,
        "evidence": evidence,
        # None when the model returned no span at all, so "did not quote" and
        # "quoted something that is not there" stay different answers.
        "evidence_verbatim": (None if not evidence else
                              " ".join(evidence.split())
                              in " ".join(text.split())),
        "rationale": t.rationale,
        "confidence": t.confidence,
        # Deliberately not driven by `confidence` - see taxonomy.REVIEW_RULES.
        "review": {
            "needed": bool(flags),
            "flags": [{"code": code, "why": why} for code, why in flags],
        },
        "meta": {
            "model": config.CLASSIFIER_MODEL,
            "prompt": f"classify/{prompt.version}",
            "latency_ms": result.latency_ms,
            "cost_usd": round(result.cost_usd, 6),
            # Both are failure handling caught in the act: attempts > 1 means a
            # retry happened, repaired means the first answer did not parse and
            # the repair call fixed it.
            "attempts": result.attempts,
            "repaired": result.repaired,
            "params_dropped": result.params_dropped,
        },
    })


# Mounted last: a StaticFiles at "/" would otherwise shadow /draft and /health.
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")
