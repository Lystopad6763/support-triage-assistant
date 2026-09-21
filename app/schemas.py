"""The output contract: one Pydantic model, and the JSON Schema sent to the model.

The same definition does both jobs. With response_format=json_schema the schema
is a constraint on generation, not a check after the fact, so a second
hand-written copy would be a second thing to drift.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.taxonomy import Category, NextStep, Priority


class Triage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    secondary_categories: list[Category] = Field(default_factory=list)
    priority: Priority
    next_step: NextStep
    evidence: str = Field(description="verbatim span copied from the ticket")
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)


def _enum(cls) -> list[str]:
    return [member.value for member in cls]


# Written out rather than derived from model_json_schema(): OpenAI-style strict
# mode wants every property required and additionalProperties false, and
# inlining the enums is shorter than post-processing $defs.
OUTPUT_SCHEMA = {
    "name": "ticket_triage",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["category", "secondary_categories", "priority",
                     "next_step", "evidence", "rationale", "confidence"],
        "properties": {
            "category": {"type": "string", "enum": _enum(Category)},
            "secondary_categories": {
                "type": "array",
                "items": {"type": "string", "enum": _enum(Category)},
            },
            "priority": {"type": "string", "enum": _enum(Priority)},
            "next_step": {"type": "string", "enum": _enum(NextStep)},
            "evidence": {"type": "string"},
            "rationale": {"type": "string"},
            "confidence": {"type": "number"},
        },
    },
}
