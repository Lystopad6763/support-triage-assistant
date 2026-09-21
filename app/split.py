"""Three specialised agents instead of one prompt, as an experiment.

THE HYPOTHESIS, AND WHY IT IS WORTH A MEASUREMENT
    v8 improved category accuracy to 84% and lost escalation recall, 83% -> 70%.
    One prompt serves three decisions, so attention spent on one is taken from
    another - the overloaded-prompt antipattern, visible as a measured trade-off
    rather than as a suspicion. Splitting removes the competition: each agent
    carries only its own rules and sees the whole ticket.

    Against that: next_step depends on the category by our own rubric (the
    routing rules are written per category). An agent that cannot see the
    category must re-derive it, which is duplicated work and an opportunity to
    disagree with the agent that owns the decision.

TWO MODES, BECAUSE ONE WOULD NOT ANSWER THE QUESTION
    parallel  all three see only the ticket. One round trip. If the triple comes
              back coherent, the dependency was weaker than the rubric implies.
    staged    category first, then priority and next_step in parallel with the
              category handed to them. Two round trips, coherent by construction.

    Comparing the two is the actual experiment: the difference between them is
    the price of the dependency.

WHAT IS ASSEMBLED
    evidence comes from the category agent - it is the span that carries the
    primary label, which is what the scorer means by evidence.
    confidence is the MINIMUM of the three, not the mean: a triple is as good as
    its weakest decision, and averaging would hide a coin-flip next_step behind a
    confident category.
    cost is the sum of every call, latency is the wall clock of the whole thing.
    A failure in ANY agent fails the ticket - a triage missing its priority is
    not a partial answer, it is an unusable one.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, ConfigDict, Field

from app import llm, taxonomy
from app.config import PROMPT_DIR, PromptConfig, Settings
from app.schemas import _enum
from app.taxonomy import Category, NextStep, Priority

SPLIT_DIR = PROMPT_DIR.parent / "split"
# The three agent prompts are one artifact with one version, independent of the
# single-call prompt: none of v1..v8 is used in this architecture, and recording
# one of their names next to these numbers would make the run unreadable later.
SPLIT_VERSION = "s1"


def split_hash() -> str:
    """One hash over all three rendered prompts, for the same reason the single
    call records one: a version name does not notice an edit."""
    import hashlib
    blob = "".join(render(name) for name, _, _ in AGENTS.values())
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


class CategoryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Category
    secondary_categories: list[Category] = Field(default_factory=list)
    evidence: str
    rationale: str
    confidence: float


class PriorityOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    priority: Priority
    evidence: str
    rationale: str
    confidence: float


class NextStepOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    next_step: NextStep
    evidence: str
    rationale: str
    confidence: float


def _schema(name: str, properties: dict) -> dict:
    common = {"evidence": {"type": "string"},
              "rationale": {"type": "string"},
              "confidence": {"type": "number"}}
    fields = {**properties, **common}
    return {"name": name, "strict": True,
            "schema": {"type": "object", "additionalProperties": False,
                       "required": list(fields), "properties": fields}}


AGENTS = {
    "category": (
        "category.txt",
        _schema("category_only", {
            "category": {"type": "string", "enum": _enum(Category)},
            "secondary_categories": {"type": "array",
                                     "items": {"type": "string",
                                               "enum": _enum(Category)}}}),
        CategoryOut),
    "priority": (
        "priority.txt",
        _schema("priority_only",
                {"priority": {"type": "string", "enum": _enum(Priority)}}),
        PriorityOut),
    "next_step": (
        "next_step.txt",
        _schema("next_step_only",
                {"next_step": {"type": "string", "enum": _enum(NextStep)}}),
        NextStepOut),
}


def render(name: str) -> str:
    """Same placeholders as the single prompt, same enum behind them: three
    agents drifting from the taxonomy would be three ways to produce a label the
    schema rejects."""
    text = (SPLIT_DIR / name).read_text(encoding="utf-8")
    for key, value in (("categories", taxonomy.categories_for_prompt()),
                       ("priorities", taxonomy.priorities_for_prompt()),
                       ("next_steps", taxonomy.next_steps_for_prompt())):
        text = text.replace("{" + key + "}", value)
    return text


def _ask(agent: str, ticket_text: str, settings: Settings, prompt: PromptConfig,
         model: str, context: str = "") -> tuple[BaseModel | None, llm.Result]:
    filename, schema, model_cls = AGENTS[agent]
    user = ticket_text if not context else f"{ticket_text}\n\n---\n{context}"
    messages = [{"role": "system", "content": render(filename)},
                {"role": "user", "content": user}]
    result = llm.Result(ticket_id=agent, model=model)
    parsed = llm.run(messages, result, prompt, settings, schema, model_cls)
    return parsed, result


def classify_split(ticket: dict, settings: Settings, model: str | None = None,
                   prompt: PromptConfig | None = None,
                   mode: str = "parallel") -> llm.Result:
    prompt = prompt or settings.prompt
    model = model or prompt.model
    out = llm.Result(ticket_id=ticket.get("ticket_id", ""), model=model)
    started = time.monotonic()
    text = ticket["text"]

    def absorb(result: llm.Result) -> None:
        out.input_tokens += result.input_tokens
        out.output_tokens += result.output_tokens
        out.cost_usd += result.cost_usd
        out.attempts = max(out.attempts, result.attempts)
        out.repaired = out.repaired or result.repaired
        if result.error and not out.error:
            out.error = f"{result.ticket_id}: {result.error}"

    with ThreadPoolExecutor(max_workers=3) as pool:
        if mode == "staged":
            category, category_result = _ask("category", text, settings, prompt, model)
            absorb(category_result)
            if category is None:
                out.latency_ms = int((time.monotonic() - started) * 1000)
                return out
            context = (f"A classifier has already decided the category of this "
                       f"ticket: {category.category.value}. Treat that as given.")
            futures = {name: pool.submit(_ask, name, text, settings, prompt,
                                         model, context)
                       for name in ("priority", "next_step")}
            answers = {name: future.result() for name, future in futures.items()}
        else:
            futures = {name: pool.submit(_ask, name, text, settings, prompt, model)
                       for name in AGENTS}
            answers = {name: future.result() for name, future in futures.items()}
            category, category_result = answers.pop("category")
            absorb(category_result)

    for parsed, result in answers.values():
        absorb(result)
    priority = answers["priority"][0]
    next_step = answers["next_step"][0]

    out.latency_ms = int((time.monotonic() - started) * 1000)
    if category is None or priority is None or next_step is None:
        out.error = out.error or "one of the three agents returned nothing"
        return out

    out.triage = llm.Triage(
        category=category.category,
        secondary_categories=category.secondary_categories,
        priority=priority.priority,
        next_step=next_step.next_step,
        evidence=category.evidence,
        rationale=" | ".join([category.rationale, priority.rationale,
                              next_step.rationale]),
        confidence=min(category.confidence, priority.confidence,
                       next_step.confidence))
    return out
