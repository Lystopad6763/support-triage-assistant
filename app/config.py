"""Settings and the prompt registry.

The defaults live here, in git, typed and reviewable; .env holds the API key and
nothing else. A model id or a temperature that exists only in someone's .env
cannot be reviewed, cannot be blamed for a change in results, and disappears
with the machine.

Every field can still be overridden by an environment variable of the same name
(TIMEOUT_SECONDS=60, PROMPT_VERSION=v2), which is what CI and a one-off
experiment need - without that override becoming the only record of it.

WHY THE PROMPT CARRIES ITS OWN MODEL AND TEMPERATURE
    Text, output format and sampling settings are one artifact: a prompt
    version. An accuracy number belongs to the pair, not to the text alone, so
    changing temperature is a version bump exactly as editing a sentence is. The
    benchmark overrides the model on purpose - that is the one place where the
    same frozen prompt is deliberately run on five of them.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
PROMPT_DIR = ROOT / "prompts" / "classify"


class PromptConfig(BaseModel):
    """One prompt version and everything that decides how it behaves."""

    version: str
    model: str
    temperature: float
    # None = send no cap at all and let the model finish. A cap on a reasoning
    # model is a trap: it is spent on thinking first, so the object gets cut off
    # mid-stream and the only symptom is a JSON error.
    max_output_tokens: int | None = None
    response_format: Literal["json_schema", "json_object", "off"]
    # Reasoning models count their internal thinking against max_output_tokens.
    # Triage is a closed-label classification, not a proof, so the cheapest
    # setting that still reads a rambling ticket correctly is the right one - and
    # the cap has to leave room for both the thinking and the object.
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None
    # temperature 0 is not determinism: the same prompt and ticket scored 68-80%
    # across four runs of v5, because the provider routes requests across
    # replicas and batches. seed is best-effort - a provider may ignore it - so
    # it is recorded per run rather than assumed.
    seed: int | None = None
    change_reason: str
    previous_version: str | None = None
    technique: str = ""
    # Held back on purpose, each one a hypothesis for the next version: a
    # baseline containing all of them cannot show which one paid for itself.
    omitted: tuple[str, ...] = ()

    # Set only by eval/ablation.py, which needs to run a variant of a version
    # without inventing a .txt file for something that is never shipped.
    text_override: str | None = None

    @property
    def text(self) -> str:
        if self.text_override is not None:
            return self.text_override
        path = PROMPT_DIR / f"{self.version}.txt"
        if not path.exists():
            raise FileNotFoundError(f"no prompt text at {path}")
        return path.read_text(encoding="utf-8")


PROMPTS: dict[str, PromptConfig] = {
    "v1": PromptConfig(
        version="v1",
        model="openai/gpt-5-mini",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort="low",
        previous_version=None,
        change_reason="Baseline. Zero-shot, the taxonomy rendered from the enum "
                      "and nothing else, so v2 has something to be measured "
                      "against.",
        technique="zero-shot, role + closed label sets + verbatim evidence",
        omitted=(
            "few-shot examples (taxonomy.examples_for_prompt)",
            "chain-of-thought",
            "the three labelling rules from the golden pass "
            "(taxonomy.rules_for_prompt)",
            "signal hints (amount stated, store named, already resolved)",
        ),
    ),
    "v2": PromptConfig(
        version="v2",
        model="openai/gpt-5-mini",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort="low",
        previous_version="v1",
        change_reason=
            "ONE change against v1: how to pick the primary category. v1 scored "
            "54% on dev with 23 category errors, and its own rationales named "
            "the cause - 'user explicitly requests a refund, SO this is "
            "primarily a refund request'. It labelled the demand instead of the "
            "fault: cancellation_failed -> refund_request x6, trial_converted "
            "-> unauthorized_charge x6. v2 states the precedence and sends the "
            "demand to secondary_categories. next_step is untouched on purpose, "
            "so that 30% can be attributed to v3.",
        technique="zero-shot + explicit precedence rule for the primary label",
        omitted=(
            "escalation criteria for next_step (v3: 26 of 35 next_step errors "
            "are escalate_to_human answered with a self-service step)",
            "a scale for confidence (0.86 when right vs 0.87 when wrong on v1, "
            "so it carries no signal)",
            "few-shot examples",
            "reasoning before the decision",
        ),
    ),
    "v3": PromptConfig(
        version="v3",
        model="openai/gpt-5-mini",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort="low",
        previous_version="v2",
        change_reason=
            "ONE change against v2: criteria for choosing next_step. v2 scored "
            "34% on it and produced escalate_to_human 5 times where the labels "
            "have it 27 times - v1 and v2 list nine actions and give no basis "
            "for picking one, so the model defaults to the self-service step. "
            "The triggers are written as facts stated in the text, not "
            "judgements, because a human reviewer has to be able to check them.",
        technique="zero-shot + precedence rule + explicit routing criteria",
        omitted=(
            "a scale for confidence",
            "few-shot examples",
            "reasoning before the decision",
        ),
    ),
    "v4": PromptConfig(
        version="v4",
        model="openai/gpt-5-mini",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort="low",
        previous_version="v3",
        change_reason=
            "ONE change against v3: priority is decided independently of "
            "next_step. v3 fixed next_step (34% -> 70%) and cost priority: the "
            "model called P1 33 times against 24 in the labels, 9 of the 14 "
            "errors being P2 answered as P1. The escalation triggers it had just "
            "been given overlap with the P1 signals, so it read 'needs a human' "
            "as 'urgent'. v4 says they are separate decisions and that P1 needs "
            "the aggravating fact stated, not inferred from tone.",
        technique="zero-shot + precedence + routing criteria + decoupled priority",
        omitted=(
            "a scale for confidence (still flat: 0.87 right vs 0.86 wrong on v3)",
            "few-shot examples",
            "reasoning before the decision",
            "KNOWN DEFECT, left for the next version so this one measures one "
            "thing: v2's precedence list says 'cancelled, unsubscribed or "
            "DELETED THE APP -> cancellation_failed', but deleting an app "
            "cancels nothing and our labels call that trial_converted. It is "
            "behind 3 of the 13 remaining category errors.",
        ),
    ),
    "v5": PromptConfig(
        version="v5",
        model="openai/gpt-5-mini",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort="low",
        previous_version="v4",
        change_reason=
            "ONE change against v4: the defect v2 introduced. v2 told the model "
            "that deleting the app counts as a cancellation; it does not stop a "
            "subscription, and our labels call a charge after a deletion "
            "trial_converted or unauthorized_charge. On v4 it produced "
            "unauthorized_charge -> cancellation_failed x4, two of those tickets "
            "saying literally 'deleted account'. v5 asks what the writer DID.",
        technique="zero-shot + precedence + routing criteria + decoupled priority",
        omitted=(
            "a scale for confidence",
            "few-shot examples",
            "reasoning before the decision",
        ),
    ),
    "v6": PromptConfig(
        version="v6",
        model="openai/gpt-5-mini",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort="low",
        previous_version="v5",
        change_reason=
            "ONE change against v5, and it is a defect, not a tuning step. The "
            "rendered taxonomy says cancellation_failed is 'cannot find OR "
            "complete cancellation, or cancelled and was billed anyway'. The "
            "precedence block added in v2 said 'took a cancellation ACTION', "
            "which is narrower and contradicts it, so the prompt held two "
            "incompatible rules. That is the most likely reason 10 of 50 tickets "
            "flip between trial_converted and cancellation_failed from run to "
            "run. v6 states both halves and keeps only the true part of the "
            "narrowing: a deletion alone is not a cancellation.",
        technique="zero-shot + precedence + routing criteria + decoupled priority",
        omitted=(
            "a scale for confidence (0.86 right vs 0.87 wrong - still unusable "
            "as a routing signal, and the fix is a scale, not a reminder)",
            "few-shot examples",
            "reasoning before the decision",
        ),
    ),
    "v7": PromptConfig(
        version="v7",
        model="openai/gpt-5-mini",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort="low",
        previous_version="v6",
        change_reason=
            "ONE change against v6: cancellation_failed needs a subscription the "
            "writer acknowledges. v6 fixed the prompt's self-contradiction and "
            "then overshot - two runs averaged 77% on category, the same as v5 "
            "within noise, while macro F1 fell 0.75 -> 0.67 and next_step 76% -> "
            "63%. The distribution says why: cancellation_failed was predicted 24 "
            "times against 21 in the labels and refund_request zero times against "
            "4. Accuracy held because cancellation_failed is the largest class, "
            "which is the exact failure macro F1 exists to expose. The tickets it "
            "broke say 'I didn't buy anything' and 'I don't have any "
            "subscription in this apps' - nothing to cancel.",
        technique="zero-shot + precedence + routing criteria + decoupled priority",
        omitted=(
            "a scale for confidence - still unusable (0.89 right vs 0.82 wrong), "
            "and syn-15 came back at 0.93 on a ticket that contradicts itself",
            "the resolved-already rule, which syn-14 fails: a ticket resolved in "
            "March was escalated",
            "any crisis instruction: syn-02 was answered as content_quality with "
            "ask_purchase_rail, and the conclusion is that crisis detection does "
            "not belong in a prompt at all - it belongs in a deterministic "
            "pre-pass that cannot be talked out of it",
            "few-shot examples",
            "reasoning before the decision",
        ),
    ),
    "v8": PromptConfig(
        version="v8",
        model="openai/gpt-5-mini",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort="low",
        previous_version="v7",
        change_reason=
            "ONE change against v7: refund_request gets a positive definition. "
            "Across four runs of v6 and v7 the class was predicted ZERO times "
            "against 4 rows in dev, and its per-class F1 is 0.00 - a label the "
            "system cannot produce at all. That is a broken contract, not a "
            "tuning gap: it accounts for 0.11 of the 0.13 macro-F1-core "
            "difference against v5 (0.72 vs 0.59). The cause is that v2 defined "
            "the class only negatively, as the fallback when no cause is "
            "identifiable, and later versions widened cancellation_failed until "
            "every ticket had a cause. v8 names the second situation our labels "
            "actually use: the refund itself is what is stuck, already refused "
            "or withheld. v7's two gains are untouched - cancellation_failed F1 "
            "0.83 -> 0.90 and trial_converted 0.77 -> 0.80.",
        technique="zero-shot + precedence + routing criteria + decoupled priority",
        omitted=(
            "a scale for confidence - the two remaining edge-case failures on v7 "
            "are both confidence, and the fix is a stated scale, not a reminder",
            "few-shot examples",
            "reasoning before the decision",
        ),
    ),
}


# Round two of the benchmark, and only round two. The main table runs every
# model on the SAME settings - temperature 0, json_schema, no reasoning, no cap -
# because that is the intersection every vendor supports, and anything else would
# compare tuning effort rather than models. These overrides exist so the second
# round, where the leaders get one adaptation each, is reproducible from the repo
# instead of from someone's shell history.
#
# The measurements behind them: "low" reasoning costs gpt-5-mini about 420 output
# tokens, and the same word gives claude-haiku-4.5 extended thinking at 2,611
# output tokens - five times the price and ten times the latency for an answer
# that scored the same. So the parameter is not portable and is never a default.
# One endpoint per model, pinned. THE RULE IS "THE VENDOR'S OWN ENDPOINT", and
# it is not a preference - it is what makes the numbers mean anything:
#
#   the schema is honoured or it is not. claude-haiku-4.5 pinned to
#   google-vertex answered our json_schema request with unparseable text; the
#   same request on anthropic answered valid JSON in 3.0s. Four of haiku's eight
#   endpoints and eight of claude-sonnet-5's ten do not declare
#   structured_outputs at all, and OpenRouter load balances into them.
#
#   the price differs inside one model id. gpt-5-mini on the same ticket cost
#   $9.62, $14.29, $16.25 and $19.07 per 10k depending on which endpoint served
#   it. A "$/10k" column without a pin is a statement about routing, not a model.
#
#   uptime differs wildly. gemini-3.1-flash-lite has an endpoint at 18.5% uptime
#   over a day and 39.8% over the last half hour, and load balancing prefers
#   cheap endpoints - "weighted by inverse square of the price" - which is
#   exactly what a flex tier is.
#
# Every pin below declares structured_outputs and is the model maker's own
# service. Special tiers (openai/flex, google-ai-studio/flex, .../priority) are
# avoided deliberately: they are a different product at a different price, and
# mixing them into a model comparison compares purchasing decisions.
MODEL_PROVIDERS: dict[str, list[str]] = {
    "openai/gpt-5-mini": ["openai"],
    "openai/gpt-5-nano": ["openai"],
    "openai/gpt-4.1-mini": ["openai"],
    "openai/gpt-4.1-nano": ["openai"],
    "openai/gpt-4o-mini-2024-07-18": ["openai"],
    "anthropic/claude-haiku-4.5": ["anthropic"],
    "anthropic/claude-sonnet-5": ["anthropic"],
    "google/gemini-2.5-flash-lite": ["google-ai-studio"],
    "google/gemini-3.1-flash-lite": ["google-ai-studio"],
    "qwen/qwen3-max": ["alibaba"],
}


MODEL_OVERRIDES: dict[str, dict] = {
    "openai/gpt-5-mini": {"reasoning_effort": "low"},
    "openai/gpt-5-nano": {"reasoning_effort": "low"},
    "google/gemini-3.1-flash-lite": {"reasoning_effort": "low"},
    "anthropic/claude-haiku-4.5": {"reasoning_effort": "low"},
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    # the only secret
    openrouter_api_key: str

    # OpenRouter speaks the OpenAI wire format, so one client reaches GPT,
    # Gemini and Claude and swapping a model is one string.
    base_url: str = "https://openrouter.ai/api/v1"
    app_title: str = "support-triage-assistant"          # attribution headers
    app_url: str = "https://github.com/Lystopad6763/support-triage-assistant"

    prompt_version: str = "v1"
    # Restrict routing to endpoints that support every parameter in the request,
    # which for a json_schema request means endpoints that really implement it.
    # Off by default: it narrows routing, and it only became usable at all once
    # we stopped sending a temperature that gpt-5 and sonnet do not support -
    # before that it answered 404 "no endpoints found" and was correct to.
    require_parameters: bool = False
    # Send every request to the endpoint named in MODEL_PROVIDERS, with fallbacks
    # off so that an outage fails visibly instead of quietly moving the
    # measurement to another machine. On by default: a number that cannot say
    # which endpoint produced it is not a measurement. Turn it off to measure
    # what a production caller would actually get from load balancing.
    pin_providers: bool = True
    timeout_seconds: float = 30.0
    max_retries: int = 3
    runs_dir: Path = ROOT / "data" / "runs"
    # Off unless a caller asks for it: a cached run reports zero cost and zero
    # spread, which is true and useless when measuring either.
    cache_path: Path = ROOT / ".cache" / "triage.sqlite"

    # Run with the FROZEN prompt, after prompt work is finished on the dev set:
    # changing prompt and model together leaves nothing to attribute a
    # difference to. Prices below are $/1M in/out from the OpenRouter catalogue
    # on 2026-09-20 and are comments only - the real cost of every call comes
    # back in the response, so nothing here has to track the catalogue.
    benchmark_models: tuple[str, ...] = (
        # Two per vendor - a cheap tier and a mid tier - across Qwen, OpenAI,
        # Anthropic and Google. Every id was probed with one live call under the
        # frozen prompt before being listed, because the catalogue's
        # structured_outputs flag turned out not to be a promise: qwen3.5-flash
        # and qwen3.5-plus both answer 400 "messages must contain the word json",
        # their provider having silently downgraded json_schema to json_object.
        # Prices are $/1M in/out from the catalogue on 2026-09-20 and are
        # comments only, since the real cost comes back per call.
        # qwen/qwen3-235b-a22b-2507 was here and is OUT. Under json_schema it
        # does not stop: 16,384 output tokens at Novita and Google, and 5,000 at
        # DeepInfra, Nebius and Parasail when capped there - finish_reason
        # "length" every time, 142-291 seconds per ticket, $29-42 per 10k for a
        # truncated object. The first probe that put it on this list measured 167
        # tokens in 3.8s: that call landed on Alibaba, the one endpoint of the ten
        # that does NOT implement structured_outputs, so the schema was downgraded
        # to json_object and the model stopped on its own. Constrained decoding is
        # what it cannot finish, and constrained decoding is what we need.
        # Doubles as the multilingual hypothesis. A quarter of both sets is not
        # English and 8% is not Latin script - Chinese, Korean, Japanese,
        # Turkish, Arabic, Vietnamese - and Qwen is the one family here trained
        # with those as a first class rather than a long tail. qwen3.5-397b was
        # the first candidate for this slot and was dropped after a probe: 8.9
        # minutes per ticket and $186 per 10k.
        "qwen/qwen3-max",                 # 0.78  / 3.90   probe: 131 out, 3.4s
        "openai/gpt-5-nano",              # 0.05  / 0.40
        "openai/gpt-5-mini",              # 0.25  / 2.00   the prompt's ruler
        # The same vendor at the same two tiers, NOT reasoning models - and the
        # pattern in the catalogue is exact: every OpenAI reasoning model (gpt-5.x,
        # o-series) lists no temperature, every non-reasoning one does. These two
        # accept temperature AND seed on all three of their endpoints (Azure and
        # OpenAI only, schema 3/3), which makes them the cleanest available test of
        # whether temperature 0 buys repeatability: same vendor, same tier, same
        # prompt, the one variable being whether the setting exists at all.
        # Probe under v8: 4.1-mini 109 out tokens, 2.3s, $9.76/10k and the correct
        # triage; 4.1-nano 91 tokens, 2.4s, $2.37/10k but route_to_safety_report on
        # a ticket with no crisis in it.
        "openai/gpt-4.1-mini",            # 0.40  / 1.60   temperature + seed
        "openai/gpt-4.1-nano",            # 0.10  / 0.40   temperature + seed
        # THE ONE MODEL HERE THAT CANNOT CHANGE UNDER US. Every other id in this
        # list is a mutable alias: "openai/gpt-4.1-mini" is whatever OpenAI
        # currently serves under that name, and the response body echoes the alias
        # back rather than a resolved snapshot, so a silent swap leaves no
        # fingerprint in the API at all. OpenRouter publishes no dated id for
        # eight of the nine - gemini-3.1-flash-lite has a -preview, which is less
        # stable rather than more, and qwen3-235b-a22b-2507 is dated and is the
        # one that never stops generating. gpt-4o-mini-2024-07-18 is the only
        # immutable, temperature-honouring, schema-supporting option in this price
        # range, and it has exactly one endpoint at 100% uptime - the most
        # reproducible configuration in the set. Its price is being a 2024
        # generation, and measuring that price is the point of including it.
        # Probe under v8: 108 out tokens, 2.6s, $3.66/10k, correct triage.
        "openai/gpt-4o-mini-2024-07-18",  # 0.15  / 0.60   dated, 1 endpoint
        # openai/gpt-oss-120b was considered and left out: temperature yes, but 24
        # endpoints across 20 providers, seed on only some and structured_outputs
        # on 18 of 24. Measuring it would measure the lottery, not the model.
        "anthropic/claude-haiku-4.5",     # 1.00  / 5.00
        "anthropic/claude-sonnet-5",      # 2.00  / 10.00
        "google/gemini-2.5-flash-lite",   # 0.10  / 0.40
        "google/gemini-3.1-flash-lite",   # 0.25  / 1.50
    )

    @property
    def prompt(self) -> PromptConfig:
        if self.prompt_version not in PROMPTS:
            raise KeyError(
                f"prompt {self.prompt_version!r} is not registered in "
                f"app/config.py; known: {sorted(PROMPTS)}")
        return PROMPTS[self.prompt_version]


def load(prompt_version: str | None = None) -> Settings:
    overrides = {"prompt_version": prompt_version} if prompt_version else {}
    return Settings(**overrides)
