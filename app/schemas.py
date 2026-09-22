"""The output contract. Two versions of it, and the JSON Schema sent to the model.

The Pydantic model and the schema do both jobs from one definition. With
response_format=json_schema the schema is a constraint on generation, not a
check after the fact, so a second hand-written copy would be a second thing to
drift.

WHY THERE ARE TWO CONTRACTS
    Structured outputs generate the fields IN SCHEMA ORDER. In `triage` the
    order is category, secondary_categories, priority, ... - so `priority` is
    written third, before `evidence` and `rationale` exist. Any chain-of-thought
    asked for in the prompt is therefore post-hoc by construction, and v2
    measured exactly that: in 70 of the 75 rows where the model itself wrote
    "no priority facts" it still answered P1 or P2.

    `triage_facts` inserts `priority_facts` immediately BEFORE `priority`, which
    makes the enumeration a generated field rather than a promise. The old
    contract is kept, unchanged, so v1 and v2 can be re-run as they were: a
    version compared under a different contract is not the same version.

    `priority_facts` carries a default, so an answer from the old contract still
    parses into the same model - an empty list means "this run did not ask".
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.taxonomy import Category, NextStep, PriorityFact, Priority


class Triage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    secondary_categories: list[Category] = Field(default_factory=list)
    # Empty under the `triage` contract, which does not ask for it.
    priority_facts: list[PriorityFact] = Field(default_factory=list)
    priority: Priority
    next_step: NextStep
    evidence: str = Field(description="verbatim span copied from the ticket")
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)


def _enum(cls) -> list[str]:
    return [member.value for member in cls]


def _props(with_facts: bool) -> dict:
    """The properties, in generation order. Order is the whole point here."""
    out = {
        "category": {"type": "string", "enum": _enum(Category)},
        "secondary_categories": {
            "type": "array",
            "items": {"type": "string", "enum": _enum(Category)},
        },
    }
    if with_facts:
        out["priority_facts"] = {
            "type": "array",
            "items": {"type": "string", "enum": _enum(PriorityFact)},
        }
    out.update({
        "priority": {"type": "string", "enum": _enum(Priority)},
        "next_step": {"type": "string", "enum": _enum(NextStep)},
        "evidence": {"type": "string"},
        "rationale": {"type": "string"},
        "confidence": {"type": "number"},
    })
    return out


def _schema(name: str, with_facts: bool) -> dict:
    # Written out rather than derived from model_json_schema(): OpenAI-style
    # strict mode wants every property required and additionalProperties false,
    # and inlining the enums is shorter than post-processing $defs.
    props = _props(with_facts)
    return {
        "name": name,
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": list(props),
            "properties": props,
        },
    }


OUTPUT_SCHEMA = _schema("ticket_triage", with_facts=False)
OUTPUT_SCHEMA_FACTS = _schema("ticket_triage_facts", with_facts=True)

# What a prompt version names in PromptConfig.contract.
CONTRACTS: dict[str, tuple[type[BaseModel], dict]] = {
    "triage": (Triage, OUTPUT_SCHEMA),
    "triage_facts": (Triage, OUTPUT_SCHEMA_FACTS),
}
