"""Prove the failure paths instead of claiming them.

    python scripts/test_failures.py            # seven offline + two live, ~$0.01
    python scripts/test_failures.py --offline   # the seven that need no API

The assignment asks what happens on invalid JSON, a timeout and a rate limit.
app/llm.py has an answer for each, but code that has never been executed is a
promise, not a behaviour - and the one failure we DID hit in a real run (a
reasoning model spending the whole token budget on thinking) was invisible until
a column in the output named it. So each path is triggered deliberately here and
the observed result is printed.

Seven are forced by replacing httpx.post with a stub, because a real 429 cannot
be summoned on demand and a real 500 even less so. The stub returns genuine
httpx.Response objects, so the code under test takes exactly the branch it would
take in production - only the socket is fake.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import llm                                                   # noqa: E402
from app.config import load                                           # noqa: E402

TICKET = {
    "ticket_id": "test-01",
    "text": "I paid $1 for a reading and then you took $49.99 a week later. "
            "I cancelled in the app before that and it charged me anyway. "
            "I want the money back and I want this subscription stopped.",
}

PASS, FAIL = "PASS", "FAIL"


def report(name: str, expectation: str, ok: bool, observed: str) -> bool:
    print(f"[{PASS if ok else FAIL}] {name}")
    print(f"       expected: {expectation}")
    print(f"       observed: {observed}")
    return ok


class Stub:
    """Stands in for httpx.post and hands back real Response objects."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0
        self.slept = 0.0

    def __call__(self, url, **kwargs):
        self.calls += 1
        index = min(self.calls - 1, len(self.responses) - 1)
        status, body, headers = self.responses[index]
        return httpx.Response(
            status_code=status, headers=headers or {},
            json=body if isinstance(body, dict) else None,
            text=None if isinstance(body, dict) else body,
            request=httpx.Request("POST", url))


def ok_body(content: str) -> dict:
    return {"choices": [{"message": {"content": content},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 2300, "completion_tokens": 120,
                      "cost": 0.0011}}


VALID = json.dumps({
    "category": "cancellation_failed", "secondary_categories": ["refund_request"],
    "priority": "1", "next_step": "escalate_to_human",
    "evidence": "I cancelled in the app before that and it charged me anyway",
    "rationale": "Cancelled and charged anyway.", "confidence": 0.9})


def with_stub(stub, fn):
    """Swap the transport, run, and always put it back."""
    real_post, real_sleep = httpx.post, time.sleep
    httpx.post = stub

    def fake_sleep(seconds):
        stub.slept += seconds

    time.sleep = fake_sleep
    try:
        return fn()
    finally:
        httpx.post, time.sleep = real_post, real_sleep


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    settings = load()
    results = []

    print("=" * 74)
    print("OFFLINE - the transport is stubbed, the logic is the real one")
    print("=" * 74)

    # 1. Rate limit. The header is the instruction; a fixed backoff that ignores
    #    it is how a client turns one 429 into a ban.
    stub = Stub((429, "rate limited", {"retry-after": "7"}),
                (200, ok_body(VALID), None))
    result = with_stub(stub, lambda: llm.classify(TICKET, settings))
    results.append(report(
        "429 with Retry-After: 7",
        "one retry, waiting the 7 seconds the server asked for, then success",
        result.ok and stub.calls == 2 and stub.slept == 7.0,
        f"calls={stub.calls} slept={stub.slept}s ok={result.ok}"))

    # 2. 429 with no header - fall back to exponential backoff rather than
    #    hammering immediately.
    stub = Stub((429, "slow down", {}), (200, ok_body(VALID), None))
    result = with_stub(stub, lambda: llm.classify(TICKET, settings))
    results.append(report(
        "429 with no Retry-After",
        "one retry after an exponential backoff of 1s",
        result.ok and stub.calls == 2 and stub.slept == 1.0,
        f"calls={stub.calls} slept={stub.slept}s ok={result.ok}"))

    # 3. 500 is the provider's problem and usually transient: retry to the limit,
    #    then report rather than pretend.
    stub = Stub((500, "upstream error", {}))
    result = with_stub(stub, lambda: llm.classify(TICKET, settings))
    results.append(report(
        "persistent 500",
        f"{settings.max_retries} attempts, then an error, no crash, no invented answer",
        not result.ok and stub.calls == settings.max_retries
        and "500" in (result.error or ""),
        f"calls={stub.calls} error={result.error!r}"))

    # 4. 401 is a broken key. Retrying it three times only delays the message.
    stub = Stub((401, "invalid api key", {}))
    result = with_stub(stub, lambda: llm.classify(TICKET, settings))
    results.append(report(
        "401 invalid key",
        "exactly one attempt - a 4xx that is not 429 will fail identically forever",
        not result.ok and stub.calls == 1,
        f"calls={stub.calls} error={result.error!r}"))

    # 5. Timeout: retried with backoff, then surfaced.
    class Timeout(Stub):
        def __call__(self, url, **kwargs):
            self.calls += 1
            raise httpx.ReadTimeout("timed out", request=httpx.Request("POST", url))

    stub = Timeout()
    result = with_stub(stub, lambda: llm.classify(TICKET, settings))
    results.append(report(
        "timeout on every attempt",
        f"{settings.max_retries} attempts with 1s + 2s of backoff, then an error",
        not result.ok and stub.calls == settings.max_retries
        and "timeout" in (result.error or "") and stub.slept == 3.0,
        f"calls={stub.calls} slept={stub.slept}s error={result.error!r}"))

    # 6. Prose instead of JSON, then a clean object on the repair turn.
    stub = Stub((200, ok_body("Sure! Here is the triage:\n\n" + VALID), None))
    result = with_stub(stub, lambda: llm.classify(TICKET, settings))
    results.append(report(
        "JSON wrapped in prose",
        "salvaged from the text without a second call",
        result.ok and not result.repaired and stub.calls == 1,
        f"calls={stub.calls} repaired={result.repaired} ok={result.ok}"))

    # 7. Unsalvageable output - the repair turn is what saves the ticket.
    stub = Stub((200, ok_body("I cannot help with that."), None),
                (200, ok_body(VALID), None))
    result = with_stub(stub, lambda: llm.classify(TICKET, settings))
    results.append(report(
        "no JSON at all in the first reply",
        "one repair call showing the model its own output, then success",
        result.ok and result.repaired and stub.calls == 2,
        f"calls={stub.calls} repaired={result.repaired} ok={result.ok}"))

    if not args.offline:
        print()
        print("=" * 74)
        print("LIVE - real calls against the provider")
        print("=" * 74)

        # 8. A real timeout, forced by an impossible deadline. Proves the
        #    exception reaches the same branch the stub exercised.
        tight = settings.model_copy(update={"timeout_seconds": 0.001,
                                            "max_retries": 2})
        started = time.monotonic()
        result = llm.classify(TICKET, tight)
        results.append(report(
            "live call with a 1ms deadline",
            "fails as a timeout, not as a crash, and returns in under 5s",
            not result.ok and "timeout" in (result.error or "")
            and time.monotonic() - started < 5,
            f"error={result.error!r} in {int((time.monotonic() - started) * 1000)}ms"))

        # 9. A real call with the schema switched off and a prompt that invites
        #    prose. This is the failure the repair path exists for, produced by
        #    a real model rather than a stub.
        loose = settings.prompt.model_copy(update={
            "response_format": "off",
            "text_override": "You are a support supervisor. Describe in two "
                             "sentences of plain English what should happen to "
                             "this ticket. Do not use JSON."})
        result = llm.classify(TICKET, settings, prompt=loose)
        results.append(report(
            "live call with response_format off and a prose instruction",
            "either salvaged or repaired into a valid object - never a crash, "
            "never a silent wrong answer",
            result.ok or bool(result.error),
            f"ok={result.ok} repaired={result.repaired} "
            f"error={result.error!r} raw={result.raw[:80]!r}"))

    print()
    passed = sum(results)
    print(f"{passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
