"""One call to OpenRouter, and the three failures the assignment asks about.

    invalid JSON   salvage the object out of the text; if that fails, ONE repair
                   call that shows the model its own output and the reason.
                   Cheaper than a blind retry and it usually works, because the
                   model was nearly right.
    timeout        retry with exponential backoff.
    rate limit     429 is not a failure, it is "later" - honour Retry-After when
                   the header is there, back off when it is not.
    no end at all  httpx applies its timeout to each socket operation, not to the
                   request as a whole, so a provider that streams slowly but
                   steadily is never cut off. One model answered in 46s under a
                   30s setting, and another never returned at all and stalled the
                   whole benchmark. run() therefore enforces one wall-clock
                   budget per TICKET and gives each attempt what is left of it -
                   a per-attempt deadline still let three attempts plus backoff
                   hold a worker for three minutes.

5xx retries; other 4xx do not, because a bad key or a malformed request fails
identically three times and the retry only delays the message.

Cost comes back in the response (usage.include), not from a price table we would
have to keep in step with the catalogue.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path
from dataclasses import dataclass
from typing import Callable

import httpx
from pydantic import BaseModel, ValidationError

from app import taxonomy
from app.cache import Cache, Entry
from app.config import MODEL_PROVIDERS, PromptConfig, Settings
from app.schemas import OUTPUT_SCHEMA, Triage

JSON_OBJECT = re.compile(r"\{.*\}", re.S)
# Written by scripts/probe_models.py from the OpenRouter catalogue. Absent or
# stale, everything is sent as before - a missing file must not change behaviour
# silently in the other direction either.
PARAMS_PATH = Path(__file__).resolve().parent.parent / "data" / "model_params.json"
_CAPABILITIES: dict | None = None
# The wall-clock deadline is a multiple of timeout_seconds rather than a second
# setting, so that raising the timeout for a slow model raises both together.
DEADLINE_FACTOR = 2.0
# The provider's own words when it has downgraded json_schema to json_object.
SCHEMA_REFUSED = re.compile(
    r"must contain the word ['\"]?json|response_format|json_object", re.I)


@dataclass
class Result:
    ticket_id: str
    model: str
    triage: Triage | None = None
    error: str | None = None
    raw: str = ""
    latency_ms: int = 0
    attempts: int = 0
    repaired: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    # Writing to the provider's prompt cache is billed separately by some vendors,
    # so a cost that counts only reads is incomplete.
    cache_write_tokens: int = 0
    # The same total split into what the input cost and what the output cost. It
    # decides where to optimise: our prompt is 2,000 tokens and the answer is 100,
    # so shortening the prompt and shortening the answer are not comparable moves.
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    # Of the input tokens, how many the provider served from its own prompt
    # cache. Two identical-prefix calls to gpt-4.1-mini measured 0 then 1,792 of
    # 1,982, and the cost fell from $0.00092 to $0.00039 - 57% for the same work.
    # That is why five runs of one prompt cost $4.87 to $6.14 per 10k with
    # identical token counts, and why a cost figure without this number cannot be
    # projected to 10,000 tickets.
    cached_input_tokens: int = 0
    # Thinking tokens, billed as output and invisible in the answer. The only way
    # to see what a reasoning model spent before writing 120 useful tokens.
    reasoning_tokens: int = 0
    cost_usd: float = 0.0
    finish_reason: str = ""
    # The provider's own word for why generation stopped, beside OpenRouter's
    # normalised one. "length" and "content_filter" both normalise to something
    # tidy, and they are opposite problems: one needs a bigger cap, the other
    # needs a different ticket.
    native_finish_reason: str = ""
    # Which service tier actually served this call. The same gpt-5-mini ticket
    # cost $9.62 and $19.07 per 10k depending on the endpoint, and until now we
    # could not tell a flex tier from the standard one after the fact.
    service_tier: str = ""
    # OpenAI's fingerprint of the backend configuration. This is the silent-swap
    # detector I said the API did not offer: every id we use is a mutable alias,
    # the response echoes the alias back, and no dated snapshot exists for eight
    # of the ten models - but if the fingerprint moves, something under the alias
    # moved with it.
    system_fingerprint: str = ""
    # Sequence confidence from the provider, where the provider offers it
    # (qwen3-max and gpt-4o-mini-2024-07-18 of our ten). The model's self-reported
    # confidence separates right from wrong by +0.002 on gpt-4.1-mini, which is
    # nothing; a real logprob is the alternative, and the mean over the answer
    # plus its least certain token is enough to test whether it separates better.
    logprob_mean: float | None = None
    logprob_min: float | None = None
    cache_hit: bool = False
    # Parameters we wanted to send and this model's endpoints do not accept, so
    # that a run file cannot claim a temperature the model never received.
    params_dropped: str = ""
    # OpenRouter load balances one model id across every provider serving it,
    # "weighted by inverse square of the price" and with no provider object sent.
    # qwen3-235b-a22b-2507 has ten of them, from 16k to 236k output tokens and
    # not all supporting json_schema, so a latency or cost attributed to the
    # MODEL without naming the endpoint is not attributable at all.
    provider: str = ""

    @property
    def ok(self) -> bool:
        return self.triage is not None


def supported(model: str) -> set[str] | None:
    """Parameters EVERY endpoint of this model supports, or None if unknown.

    The intersection, not the union: OpenRouter load balances across endpoints
    and drops what the chosen one does not support, so a parameter honoured by
    only some of them takes effect on some calls and not others. That is worse
    than not sending it, because the resulting numbers are a blend of two
    settings with nothing in the response to say which call got which.
    """
    global _CAPABILITIES
    if _CAPABILITIES is None:
        try:
            with open(PARAMS_PATH, encoding="utf-8") as handle:
                _CAPABILITIES = json.load(handle).get("models", {})
        except (OSError, json.JSONDecodeError):
            _CAPABILITIES = {}
    entry = _CAPABILITIES.get(model)
    return set(entry["all"]) if entry else None


def dropped_params(model: str, prompt: PromptConfig) -> list[str]:
    """What we would like to send and this model cannot receive."""
    caps = supported(model)
    if caps is None:
        return []
    wanted = ["temperature"]
    if prompt.seed is not None:
        wanted.append("seed")
    if prompt.max_output_tokens:
        wanted.append("max_tokens")
    if prompt.reasoning_effort:
        # Four of our ten models do not take a reasoning parameter at all -
        # gpt-4.1-mini, gpt-4.1-nano, gpt-4o-mini and qwen3-max - and we were
        # sending "reasoning": {"effort": "low"} to every one of them. Dropped
        # silently, exactly as temperature was, and it would have made
        # require_parameters answer 404 for them too.
        wanted.append("reasoning")
    return [name for name in wanted if name not in caps]


def render(prompt: PromptConfig) -> str:
    """Fill the prompt's placeholders from the taxonomy, so the enum stays the
    single source: a prompt that offers a category the schema rejects produces
    confident output that cannot be parsed."""
    text = prompt.text
    for key, value in (
        ("categories", taxonomy.categories_for_prompt()),
        ("priorities", taxonomy.priorities_for_prompt()),
        ("next_steps", taxonomy.next_steps_for_prompt()),
        ("examples", taxonomy.examples_for_prompt()),
        ("rules", taxonomy.rules_for_prompt()),
    ):
        text = text.replace("{" + key + "}", value)
    return text


def run(messages: list[dict], result: Result, prompt: PromptConfig,
        settings: Settings, schema: dict = OUTPUT_SCHEMA,
        model_cls: type[BaseModel] = Triage,
        notify: Callable[[str], None] | None = None) -> BaseModel | None:
    """The retry, repair and accounting loop, for any schema.

    Extracted so that the split-agent architecture in app/split.py gets the same
    failure handling as the single call: three specialised agents that each
    reinvent the 429 policy would be three chances to get it wrong, and the
    failure paths are the part of this system that is actually proven.
    """
    strict = False
    parsed = None
    result.params_dropped = ",".join(dropped_params(result.model, prompt))
    # The deadline belongs to the TICKET, not to the attempt. Bounding each
    # attempt separately let three attempts plus backoff hold one worker for
    # three minutes: a benchmark printed nothing for 112 seconds while a single
    # ticket burned attempt after attempt against a slow endpoint. Each attempt
    # now gets whatever is left of one budget, and a ticket that cannot answer
    # inside it is a failed ticket - which is a finding, not an accident.
    budget = settings.timeout_seconds * DEADLINE_FACTOR
    deadline_at = time.monotonic() + budget
    expired = f"timeout: no answer within the {budget:.0f}s budget for one ticket"

    def sleep_within(seconds: float) -> None:
        """Never back off past the deadline we are about to check."""
        time.sleep(max(0.0, min(seconds, deadline_at - time.monotonic())))

    for attempt in range(settings.max_retries):
        result.attempts = attempt + 1
        last = attempt + 1 == settings.max_retries
        left = deadline_at - time.monotonic()
        if left <= 0.5:
            result.error = result.error or expired
            if notify:
                notify(f"attempt {attempt + 1} not started: {result.error}")
            break
        try:
            response = _post(messages, result.model, prompt, settings,
                             strict_provider=strict, schema=schema, deadline=left)
        except httpx.TimeoutException as exc:
            if notify:
                notify(f"attempt {attempt + 1} timed out: {exc}")
            if last:
                result.error = expired
                break
            sleep_within(_backoff(attempt))
            continue
        except httpx.HTTPError as exc:
            result.error = f"transport: {exc}"
            break

        if response.status_code == 429 or response.status_code >= 500:
            wait = _retry_after(response) or _backoff(attempt)
            if notify:
                notify(f"attempt {attempt + 1}: HTTP {response.status_code}, "
                       f"waiting {wait:.0f}s")
            if last:
                result.error = f"HTTP {response.status_code}: {response.text[:200]}"
                break
            sleep_within(wait)
            continue
        if response.status_code >= 400:
            if (response.status_code == 400 and not strict
                    and SCHEMA_REFUSED.search(response.text or "")):
                strict = True
                if notify:
                    notify(f"attempt {attempt + 1}: the provider refused the "
                           f"schema, retrying with require_parameters")
                continue
            result.error = f"HTTP {response.status_code}: {response.text[:200]}"
            break

        body = response.json()
        result.provider = body.get("provider") or ""
        result.service_tier = body.get("service_tier") or ""
        result.system_fingerprint = body.get("system_fingerprint") or ""
        _record_usage(result, body)
        choice = body["choices"][0]
        result.finish_reason = choice.get("finish_reason", "")
        result.native_finish_reason = choice.get("native_finish_reason", "")
        _record_logprobs(result, choice)
        result.raw = choice["message"].get("content") or ""
        try:
            parsed = _parse(result.raw, model_cls)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            repaired = _repair(messages, result, prompt, settings, str(exc),
                               schema, model_cls,
                               deadline=deadline_at - time.monotonic())
            if repaired is not None:
                parsed, result.repaired = repaired, True
        break
    return parsed


def classify(ticket: dict, settings: Settings, model: str | None = None,
             prompt: PromptConfig | None = None,
             cache: Cache | None = None,
             notify: Callable[[str], None] | None = None) -> Result:
    prompt = prompt or settings.prompt
    result = Result(ticket_id=ticket.get("ticket_id", ""),
                    model=model or prompt.model)
    system = render(prompt)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": ticket["text"]},
    ]
    started = time.monotonic()

    # The key holds the rendered prompt, not its version name: a version edited
    # in place would otherwise serve answers from the prompt it used to be.
    prompt_sha = hashlib.sha256(system.encode("utf-8")).hexdigest()[:16]
    key = None
    if cache is not None:
        key = Cache.key(prompt_sha, result.model, prompt.temperature,
                        prompt.response_format, prompt.reasoning_effort,
                        ticket["text"])
        hit = cache.get(key)
        if hit is not None:
            result.triage = Triage.model_validate(hit.triage)
            result.cache_hit = True
            result.attempts = 0
            result.input_tokens = hit.input_tokens
            result.output_tokens = hit.output_tokens
            result.latency_ms = int((time.monotonic() - started) * 1000)
            # cost stays 0: the money was spent on the run that filled the entry,
            # and counting it twice would flatter every projection built on it.
            return result

    result.triage = run(messages, result, prompt, settings)

    result.latency_ms = int((time.monotonic() - started) * 1000)
    if cache is not None and key and result.ok:
        cache.put(key, prompt_sha, result.model, ticket["text"],
                  Entry(triage=result.triage.model_dump(mode="json"),
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        cost_usd=result.cost_usd,
                        latency_ms=result.latency_ms))
    return result


def _post(messages: list[dict], model: str, prompt: PromptConfig,
          settings: Settings, max_tokens: int | None = None,
          strict_provider: bool = False,
          schema: dict = OUTPUT_SCHEMA,
          deadline: float | None = None) -> httpx.Response:
    """The request, under a real deadline.

    httpx's timeout bounds each socket operation. A response that keeps trickling
    bytes resets the read clock every chunk and can run for minutes, which is how
    a benchmark run stalled on one model with nothing in the logs. The request is
    therefore submitted to a single worker and abandoned if the wall clock passes
    the deadline; the abandoned thread finishes on its own and its result is
    dropped. Abandoning is not as clean as cancelling, but a hung call that the
    caller can see is better than one it cannot.
    """
    deadline = (settings.timeout_seconds * DEADLINE_FACTOR
                if deadline is None else max(0.5, deadline))
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_send, messages, model, prompt, settings, max_tokens,
                             strict_provider, schema)
        try:
            return future.result(timeout=deadline)
        except FutureTimeout:
            raise httpx.ReadTimeout(
                f"no response within the {deadline:.0f}s wall-clock deadline",
                request=httpx.Request("POST", f"{settings.base_url}/chat/completions"))


def _send(messages: list[dict], model: str, prompt: PromptConfig,
          settings: Settings, max_tokens: int | None = None,
          strict_provider: bool = False,
          schema: dict = OUTPUT_SCHEMA) -> httpx.Response:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": prompt.temperature,
        "usage": {"include": True},
    }
    cap = max_tokens or prompt.max_output_tokens
    if cap:
        payload["max_tokens"] = cap
    if prompt.seed is not None:
        payload["seed"] = prompt.seed
    # Send only what the model can receive. Not politeness: an unsupported field
    # is dropped by OpenRouter without a word - "temperature": 0 never reached
    # gpt-5-mini, whose endpoints do not support it - and the same field makes
    # provider.require_parameters answer 404, because no endpoint can satisfy a
    # request asking for it.
    caps = supported(model)
    if caps is not None:
        for name in ("temperature", "seed", "max_tokens", "reasoning"):
            if name in payload and name not in caps:
                payload.pop(name)
        # Two of the ten models support logprobs, and one of them leads the
        # benchmark. They cost no tokens, so the only reason not to ask is that
        # the endpoint would reject the field.
        if "logprobs" in caps:
            payload["logprobs"] = True
            if "top_logprobs" in caps:
                payload["top_logprobs"] = 1
    if prompt.reasoning_effort:
        payload["reasoning"] = {"effort": prompt.reasoning_effort}
    if prompt.response_format == "json_schema":
        payload["response_format"] = {"type": "json_schema",
                                      "json_schema": schema}
    elif prompt.response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}

    # Routing is part of the request, not an afterthought: with nothing set here
    # OpenRouter load balances across every endpoint serving this id, and the
    # endpoints differ in whether they implement json_schema, in price and in
    # uptime. See MODEL_PROVIDERS for the measured cases.
    routing: dict = {}
    pinned = MODEL_PROVIDERS.get(model) if settings.pin_providers else None
    if pinned:
        routing["only"] = pinned
        routing["allow_fallbacks"] = False
    if prompt.response_format == "json_schema" and (settings.require_parameters
                                                    or strict_provider):
        # Endpoints that support EVERY parameter in the request, which for a
        # json_schema request means the ones that really implement it. Sent
        # always when the setting is on, and otherwise only as the one-shot
        # retry for a provider that downgraded the schema and then rejected the
        # request for not containing the word "json". It used to answer 404 "no
        # endpoints found" - correctly, because we were also asking for a
        # temperature that gpt-5 and sonnet do not support.
        routing["require_parameters"] = True
    if routing:
        payload["provider"] = routing
    return httpx.post(
        f"{settings.base_url}/chat/completions",
        json=payload,
        timeout=settings.timeout_seconds,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "HTTP-Referer": settings.app_url,
            "X-Title": settings.app_title,
        },
    )


def _parse(raw: str, model_cls: type[BaseModel] = Triage) -> BaseModel:
    """Accept what models actually send: the object alone, a fenced block, or a
    preamble. Anything else raises and the caller repairs once."""
    try:
        return model_cls.model_validate_json(raw)
    except (ValidationError, ValueError):
        match = JSON_OBJECT.search(raw)
        if not match:
            raise ValueError("no JSON object in output")
        return model_cls.model_validate(json.loads(match.group(0)))


def _repair(messages: list[dict], result: Result, prompt: PromptConfig,
            settings: Settings, why: str, schema: dict = OUTPUT_SCHEMA,
            model_cls: type[BaseModel] = Triage,
            deadline: float | None = None) -> BaseModel | None:
    """One more turn, showing the model its own output and why it failed.

    If a cap is set at all and truncation was the cause, it is doubled for this
    turn only: retrying under the same cap would cut the object in the same
    place. v1 sets no cap, so this path is for a version that reintroduces one.
    """
    cap = prompt.max_output_tokens
    if result.finish_reason == "length":
        why += " (the output was cut off at the token limit)"
        cap = cap * 2 if cap else None
    follow_up = messages + [
        {"role": "assistant", "content": result.raw},
        {"role": "user", "content":
            f"That was not usable: {why}. Send the same triage again as one "
            f"JSON object and nothing else - no prose, no code fence."},
    ]
    try:
        response = _post(follow_up, result.model, prompt, settings, max_tokens=cap,
                         schema=schema, deadline=deadline)
        if response.status_code >= 400:
            result.error = f"invalid JSON; repair got HTTP {response.status_code}"
            return None
        body = response.json()
        result.provider = body.get("provider") or result.provider
        _record_usage(result, body)
        result.raw = body["choices"][0]["message"].get("content") or ""
        return _parse(result.raw, model_cls)
    except (httpx.HTTPError, ValidationError, ValueError,
            json.JSONDecodeError, KeyError) as exc:
        result.error = f"invalid JSON, repair failed: {exc}"
        return None


def _record_usage(result: Result, body: dict) -> None:
    """Accumulated, not assigned: a repair call is part of what the ticket cost."""
    usage = body.get("usage") or {}
    result.input_tokens += usage.get("prompt_tokens", 0)
    result.output_tokens += usage.get("completion_tokens", 0)
    result.cost_usd += float(usage.get("cost") or 0.0)
    prompt_details = usage.get("prompt_tokens_details") or {}
    result.cached_input_tokens += int(prompt_details.get("cached_tokens") or 0)
    result.cache_write_tokens += int(prompt_details.get("cache_write_tokens") or 0)
    completion_details = usage.get("completion_tokens_details") or {}
    result.reasoning_tokens += int(completion_details.get("reasoning_tokens") or 0)
    costs = usage.get("cost_details") or {}
    result.input_cost_usd += float(costs.get("upstream_inference_prompt_cost") or 0)
    result.output_cost_usd += float(
        costs.get("upstream_inference_completions_cost") or 0)


def _record_logprobs(result: Result, choice: dict) -> None:
    """Keep two numbers, not the whole distribution.

    A 112-token answer with three alternatives per token is 300 numbers per
    ticket, and storing them would make a run file unreadable for a signal we can
    summarise: the mean logprob of the answer is its overall confidence, and the
    minimum is the single token the model was least sure of - which for a schema
    answer is usually the category value itself, since the punctuation and the key
    names are forced.
    """
    logprobs = (choice.get("logprobs") or {}).get("content") or []
    values = [item["logprob"] for item in logprobs
              if isinstance(item.get("logprob"), (int, float))]
    if not values:
        return
    result.logprob_mean = sum(values) / len(values)
    result.logprob_min = min(values)


def _backoff(attempt: int) -> float:
    return min(2.0 ** attempt, 30.0)


def _retry_after(response: httpx.Response) -> float | None:
    header = response.headers.get("retry-after")
    if not header:
        return None
    try:
        return min(float(header), 60.0)
    except ValueError:
        return None
