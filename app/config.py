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
    # The frozen set this version is scored on. Named here so a version cannot
    # quietly be compared against a different set than the one before it.
    # Which output contract this version speaks, from app.schemas.CONTRACTS.
    # Versioned with the prompt because the field ORDER inside the schema decides
    # what the model has written by the time it commits to a label - so a
    # contract change is a behaviour change, not a refactor.
    contract: str = "triage"
    tested_on: str = "golden_v1 + synthetic_v1 (250 rows)"
    # The run that produced this version's score, not the score itself. A number
    # copied in by hand drifts from the run that made it the moment either is
    # touched; a pointer cannot. eval/run.py writes the summary, the report
    # joins the two.
    eval_run: str | None = None
    # Held back on purpose, each one a hypothesis for the next version: a
    # baseline containing all of them cannot show which one paid for itself.
    omitted: tuple[str, ...] = ()

    # Set only by eval/ablation.py, which needs to run a variant of a version
    # without inventing a .txt file for something that is never shipped.
    text_override: str | None = None

    @property
    def text(self) -> str:
        """The prompt body, .md preferred over .txt.

        Markdown because the file is read by people in the repository and by
        GitHub, and because the body already uses headings - the model receives
        a string either way and the extension never reaches the API. .txt is
        still accepted so the versions in git history load unchanged.

        Whatever is in the file is SPOKEN TO THE MODEL, every run. Metadata -
        why the version exists, what it scored, what it holds back - belongs in
        this object, not in the file: a change_reason inside the prompt is an
        instruction the model will try to follow.
        """
        if self.text_override is not None:
            return self.text_override
        for suffix in (".md", ".txt"):
            path = PROMPT_DIR / f"{self.version}{suffix}"
            if path.exists():
                return path.read_text(encoding="utf-8")
        raise FileNotFoundError(
            f"no prompt text at {PROMPT_DIR / self.version}.md or .txt")


PROMPTS: dict[str, PromptConfig] = {
    # v1 -- v8 of the first pass are gone with the taxonomy they classified into
    # (11 categories, ASK_PURCHASE_RAIL, priority as "1"/"2"/"3"). They stay in
    # git history at 58a8bb4; their error analysis does not transfer, because
    # every error was an error about labels that no longer exist.
    "v1": PromptConfig(
        version="v1",
        # The dated snapshot, not the floating alias: an alias can be
        # repointed by the provider, and a number that moved for that reason
        # looks exactly like a prompt that got worse.
        model="openai/gpt-4o-mini-2024-07-18",
        # Chosen for prompt iteration because it ACCEPTS temperature 0. The
        # gpt-5 family reasons internally and rejects a temperature other than
        # 1, which adds run-to-run spread on top of every prompt edit - the one
        # thing you cannot afford while attributing a delta to one change.
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort=None,          # not a reasoning model
        # Probed 2026-09-21: this model accepts seed, and it has exactly ONE
        # endpoint, so there is no load balancing to blend two settings. Seed is
        # best-effort - a provider may ignore it - so it is recorded per run
        # rather than assumed, but asking costs nothing.
        seed=20260922,
        previous_version=None,
        change_reason="Baseline for the 6/3/7 taxonomy. Zero-shot: the "
                      "vocabulary rendered from the enum, the ordered category "
                      "tests, the six priority facts and the constraint table, "
                      "and nothing else - so that every later version has one "
                      "attributable change.",
        technique="zero-shot, closed label sets, ordered tests, verbatim "
                  "evidence, explicit fallback to route_to_human_review",
        # Carried over from the first pass because it cost a measurement to
        # learn and does not depend on the taxonomy: `confidence` asked for
        # without a scale is uninformative - it averaged 0.86 when the answer
        # was right and 0.87 when it was wrong (58a8bb4). It stays in the
        # schema as a diagnostic, but nothing may gate on it until a version
        # defines what each value means.
        omitted=(
            "few-shot examples (taxonomy.examples_for_prompt)",
            "the four cross-field rules (taxonomy.rules_for_prompt): tone is "
            "not a signal, ticket text is data not instruction, length is not "
            "a signal, the tie-break on what the writer asks for",
            "chain-of-thought before the answer",
            "currency normalisation hint for large_amount",
        ),
    ),
    "v2": PromptConfig(
        version="v2",
        model="openai/gpt-4o-mini-2024-07-18",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort=None,
        seed=20260922,
        previous_version="v1",
        change_reason="ONE change against v1: the priority section becomes a "
                      "two-step procedure - enumerate the facts you can quote, "
                      "then apply the mapping - plus three denials. v1 never "
                      "answered P3 at all (0 of 11 on the first 20 dev rows, "
                      "accuracy 0.200 against a majority baseline of 0.550) "
                      "and its rationales derived the priority from the "
                      "CATEGORY: 'app_defect fired' -> P2, 'they want a refund, "
                      "indicating urgency' -> P1, and one row stated 'no "
                      "priority fact present' and still answered P2. So the "
                      "rule was present but not binding, and the mapping had "
                      "to become an order of operations.",
        technique="zero-shot + ordered procedure for the one field that failed",
        omitted=(
            "few-shot examples (taxonomy.examples_for_prompt)",
            "the four cross-field rules (taxonomy.rules_for_prompt)",
            "chain-of-thought before the answer",
            "a priority_facts[] array in the schema - held for v3 on purpose: "
            "changing the prompt and the output contract together would leave "
            "nothing to attribute the difference to",
        ),
    ),
    "v3": PromptConfig(
        version="v3",
        model="openai/gpt-4o-mini-2024-07-18",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort=None,
        seed=20260922,
        contract="triage_facts",
        previous_version="v2",
        change_reason="ONE change against v2: the output contract. v2 asked for "
                      "the enumeration in prose and got it - the model wrote "
                      "'no priority facts' in 75 of 157 dev rows - and then "
                      "ignored the mapping in 70 of those 75 (93%), answering "
                      "P1 31 times and P2 39. Priority accuracy 0.223 against "
                      "a majority baseline of 0.550; applying the mapping to "
                      "the model's OWN list would have given ~0.516. The cause "
                      "is field order: structured outputs generate in schema "
                      "order, so `priority` was written third, before evidence "
                      "and rationale existed, which makes any chain-of-thought "
                      "in the prompt post-hoc by construction. v3 inserts "
                      "priority_facts[] immediately before priority, turning "
                      "the enumeration into a generated field and the "
                      "contradiction into a countable defect.",
        technique="zero-shot + chain-of-thought moved into the output contract",
        omitted=(
            "few-shot examples (taxonomy.examples_for_prompt) - the lecture's "
            "classification advice asks for one example per category and "
            "fewshot_v1.json already holds all six plus all seven steps; it is "
            "the strongest next move and therefore has to be measured alone",
            "shortening the priority section now that the enumeration lives in "
            "the schema (the overloaded-prompt antipattern)",
            "moving rationale before the labels as well",
        ),
    ),
    "v4": PromptConfig(
        version="v4",
        model="openai/gpt-4o-mini-2024-07-18",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort=None,
        seed=20260922,
        contract="triage_facts",
        previous_version="v3",
        change_reason="TWO edits, in two different fields' sections, kept in one "
                      "version because the metrics that judge them are "
                      "disjoint: one moves `priority`, the other moves table "
                      "violations, so a failure is still attributable. (1) v3 "
                      "fixed the mapping and the error moved into the "
                      "enumeration: `still_bleeding` was claimed 40 times on "
                      "157 dev rows and 22 of those were gold P3, because the "
                      "model reads the BILLING PERIOD NAME as recurrence - "
                      "'charged 39.90 for a week', '$8.95 for One Week'. That "
                      "is the same trap our own regex fell into on the word "
                      "`monthly` (LABELLING.md section 9), reproduced "
                      "independently, so the fact needed its own test: two "
                      "charges with dates or amounts, or an explicit statement "
                      "that charges continue. The mapping is also restated as "
                      "three first-match lines, because the middle one - a soft "
                      "fact alone is P2 - was skipped in all 9 "
                      "self-contradictions. (2) All 9 table violations were "
                      "`route_to_human_review` from categories that forbid it, "
                      "and that was OUR bug: the output section invited the "
                      "step while the table allows it only with `other`. Now "
                      "stated: the step and the category travel together.",
        technique="zero-shot + CoT in the contract + a per-fact test for the "
                  "one fact that over-fires",
        omitted=(
            "few-shot examples (taxonomy.examples_for_prompt) - still the "
            "strongest untried move, and still held back so it can be measured "
            "alone",
            "shortening the priority section (overloaded-prompt antipattern) - "
            "v4 made it longer, not shorter, which makes the cut worth "
            "measuring afterwards",
            "moving rationale before the labels",
            "promoting the sharpened still_bleeding wording into taxonomy.py - "
            "that would change what v1-v3 render and destroy the comparison; "
            "it moves there when a version is frozen",
        ),
    ),
    "v5": PromptConfig(
        version="v5",
        model="openai/gpt-4o-mini-2024-07-18",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort=None,
        seed=20260922,
        contract="triage_facts",
        previous_version="v4",
        change_reason="SUBTRACTION, and it is a measurement rather than a "
                      "retreat. v4 carried two edits inside one field, and the "
                      "evidence says the gain came from the mapping rewrite, "
                      "not from the still_bleeding test that was supposed to "
                      "deliver it: claims of that fact went UP 40 -> 63, gold-P3 "
                      "rows answered P2 went UP 22 -> 30 (27 of them via "
                      "still_bleeding), while P1 answers fell 50 -> 24, which is "
                      "the mapping's work. The block listed the exact phrases "
                      "the model was failing on as forbidden, and the lecture's "
                      "antipattern list is explicit that a bare prohibition is "
                      "not a concrete instruction and that negatives work only "
                      "alongside positives. So it comes out. If priority holds "
                      "near 0.70 the block was dead weight and the prompt is "
                      "1,000 characters and ~$0.5/10k cheaper for free; if "
                      "priority drops, the block was carrying something and has "
                      "to be rewritten as a positive example instead of a ban. "
                      "Either outcome settles the attribution v4 left open.",
        technique="zero-shot + CoT in the contract + mapping as first-match; "
                  "no per-fact prohibitions",
        omitted=(
            "few-shot examples (taxonomy.examples_for_prompt) - next, and now "
            "aimed at a measured target: 10 rows where gold is P2 and the model "
            "returned P3 with an EMPTY list, i.e. under-firing, which a ban "
                  "cannot fix and an example can",
            "moving rationale before the labels",
            "anything about the 12 invented evidence spans, which no version has "
            "moved yet",
        ),
    ),
    "v6": PromptConfig(
        version="v6",
        model="openai/gpt-4o-mini-2024-07-18",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort=None,
        seed=20260922,
        contract="triage_facts",
        previous_version="v4",
        change_reason="FEW-SHOT, and it descends from v4, not v5: the repeats "
                      "run settled that. Three runs of v5 put the headline in "
                      "0.7636-0.7660 - a range of 0.0024 - while v4 sits at "
                      "0.775, above the whole band, and on priority 0.700 "
                      "against 0.6709-0.6827. So v5's subtraction LOST "
                      "something, and the earlier 'dead weight' reading was "
                      "drawn from a noise estimate that had been derived from "
                      "the very difference it was used to dismiss. What the "
                      "block actually did is the opposite of what it says: "
                      "false facts on gold-P3 rows did not move (v4 32, v5 "
                      "30-33, of which still_bleeding 27 vs 26-28), while "
                      "under-firing did (gold P2 answered P3 with an empty "
                      "list: v4 10, v5 13-16). A long test naming the fact nine "
                      "times RAISED claims of it, 54-57 -> 63, and the extra "
                      "claims happened to land on real P2 rows. The lecture's "
                      "antipattern with the sign reversed: a prohibition primes "
                      "rather than suppresses. Both diseases are therefore "
                      "about the fact list and neither is reachable by prose - "
                      "32 false claims have stood unmoved through four "
                      "versions. So: 9 worked examples, rendered from the "
                      "fewshot set, each showing priority_facts WITH the words "
                      "that put each fact on the list, and four of the nine "
                      "showing an empty list on a ticket that looks urgent. "
                      "Four negatives against five positives because the "
                      "over-firing side is the bigger one in absolute rows. "
                      "Cost is the known risk: the block is 3,839 characters, "
                      "the prompt goes 9,930 -> ~13,800 and ~$2.99 -> ~$4.0 per "
                      "10k. If it wins, trimming the block is the next "
                      "measurement and a cheap one; if it does not, few-shot is "
                      "not the lever here and that is worth reporting too.",
        technique="few-shot (9 examples, facts shown with their quotes) + CoT in "
                  "the contract + mapping as first-match + per-fact test",
        omitted=(
            "hardship has no example - the fewshot set contains no row with it, "
            "and borrowing one from dev or golden would leak a scored row into "
            "the prompt. Its definition still arrives via {priorities}",
            "route_to_human_review has no example either, deliberately: it is "
            "the step the model over-uses, and v4 just proved that showing a "
            "label makes it more likely, not less. The one `other` example maps "
            "to bug_report instead",
            "trimming the block - that is the next version if this one wins, "
            "measured alone",
            "moving rationale before the labels",
            "anything about the invented evidence spans, still untouched after "
            "five versions",
        ),
    ),
    "v7": PromptConfig(
        version="v7",
        model="openai/gpt-4o-mini-2024-07-18",
        temperature=0.0,
        max_output_tokens=None,
        response_format="json_schema",
        reasoning_effort=None,
        seed=20260922,
        contract="triage_facts",
        previous_version="v4",
        change_reason="NEGATIVE EXAMPLES ONLY, and it is a test of one mechanism "
                      "rather than a hope. v6 put nine examples in and lost "
                      "0.037 against a measured noise range of 0.0024. The cause "
                      "was not the missing hardship example - claims of that "
                      "fact went 10 -> 11, unmoved - it was the examples "
                      "themselves acting as frequency anchors: one `deadline` "
                      "example took claims of it from 1 to 31, one "
                      "`escalated_out` example from 15 to 35. P1 recall rose "
                      "(23/25 against 20/25) while P1 precision collapsed, 4 "
                      "false P1 -> 21, and F1(P1) fell 0.816 -> 0.667. So a "
                      "shown fact becomes an available move, and over-claiming a "
                      "HARD fact costs far more than over-claiming a soft one. "
                      "v6 did cure the target disease - still_bleeding claims "
                      "63 -> 41 - and it took table violations to 0, the first "
                      "version to do so. v7 keeps only the half that cannot "
                      "backfire: the four examples with an EMPTY list, with "
                      "every fact NAME stripped from their reasons, since the "
                      "name is the prime. They aim at the largest error class in "
                      "the run, untouched since v2: 32 gold-P3 rows carrying a "
                      "claimed fact. The block is 1,826 characters against v6's "
                      "3,839. Predicted, and falsifiable: false facts on gold-P3 "
                      "rows fall, while `deadline` and `escalated_out` claims "
                      "stay where v4 left them, at 1 and 15. The risk is the "
                      "mirror image - four empty lists in a row priming "
                      "emptiness and costing P2 and P1 recall - so the framing "
                      "states the real 58/42 split instead of letting four "
                      "examples imply it.",
        technique="four negative examples (no fact names shown) + CoT in the "
                  "contract + mapping as first-match + per-fact test",
        omitted=(
            "the five positive examples from v6 - they are what did the damage, "
            "and they are held back rather than deleted: v6 stays re-runnable "
            "and its annotations are untouched",
            "hardship still has no example, and v6 showed that costs nothing",
            "anything about the invented evidence spans, still untouched after "
            "six versions",
            "moving rationale before the labels",
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


# --- what actually ships ------------------------------------------------------
# The frozen pair, and it is NOT the pair the prompt was written against. The
# prompt was tuned on gpt-4o-mini; the benchmark then put that model 9th of 10.
#
# Round 2, all 157 dev rows, prompt v4 held identical for every model:
#
#   model                  core   all    F1 prio   invented   $/10k   p50
#   claude-sonnet-5        0.838  0.719  0.710     6          145.16  7608
#   gpt-5-mini             0.819  0.709  0.757     9           26.35  13172
#   gemini-3.1-flash-lite  0.803  0.725  0.786     2            8.65  1640
#   gpt-4o-mini (base)     0.775  0.642  0.700     12           2.99  2172
#
# The two headline numbers disagree about the winner - core says sonnet by
# 0.035, all-classes says gemini by 0.006 - so quality is a tie, and the tie is
# broken by the axes that are not noisy: gemini leads the PRIORITY field (0.786
# against 0.710), invents the fewest quotes (2 against 6 and 9), answers fastest
# of all four including the base, and costs 17x less than sonnet. False facts on
# gold-P3 rows: 6 of 92 against sonnet's 7 and the base's 32.
#
# What is NOT claimed: that gemini is better than sonnet. Per-model spread was
# not measured (~$7, mostly sonnet), so the honest statement is that they are
# indistinguishable on quality and gemini wins everything else.
#
# Known weaknesses of this pair, carried into the report rather than hidden:
# next_step is its worst field (0.790, below all three others), and it finds 14
# of 25 gold P1 where the base found 20. Precision and recall trade cleanly
# across the whole table - the more conservative the model, the more P1 it
# misses - and a missed P1 is the most expensive error this system makes.
CLASSIFIER_PROMPT = "v4"
CLASSIFIER_MODEL = "google/gemini-3.1-flash-lite"
