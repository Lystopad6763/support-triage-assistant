"""Text to vectors, through the same OpenRouter key as everything else.

OpenRouter does serve /embeddings, and finding that out took a request rather
than a catalogue lookup: /models returns 440 chat models and not one embedding
model, and ?category=embedding answers 400. So the list of what is available
here was probed model by model, and these three are what survived - cohere and
mistral embeddings are not on OpenRouter at all ("does not exist"), and
qwen3-embedding-0.6b has no endpoint.

    baai/bge-m3                     1024 dims   $0.010 / 1M   multilingual
    openai/text-embedding-3-small   1536 dims   $0.020 / 1M
    qwen/qwen3-embedding-8b         4096 dims   $0.010 / 1M   multilingual

The whole knowledge base is 22k tokens, so indexing it on all three costs
$0.0006 in total. That is the reason the choice of encoder is measured here
rather than argued: at this size the experiment is cheaper than the opinion.

WHY THIS IS NOT IN llm.py
    Different endpoint, different request body, different failure surface, and
    nothing in the chat path (schema constraints, JSON repair, reasoning
    effort) applies to it. The two share a key and a base url, which is not
    enough to share a module.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from app.config import Settings

# Known dimensions, used only to catch a provider quietly changing one under us.
# A vector of unexpected width fails the index build rather than being written
# into a file that then compares against nothing.
DIMENSIONS = {
    "baai/bge-m3": 1024,
    "openai/text-embedding-3-small": 1536,
    "qwen/qwen3-embedding-8b": 4096,
}

# One request carries this many texts. The whole corpus is 84 documents, so this
# is about being polite to the endpoint rather than about throughput.
BATCH = 32


@dataclass
class EmbedResult:
    model: str
    vectors: list[list[float]] = field(default_factory=list)
    tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    requests: int = 0

    @property
    def dims(self) -> int:
        return len(self.vectors[0]) if self.vectors else 0


def embed(texts: list[str], model: str, settings: Settings) -> EmbedResult:
    """Embed texts in order, with the same retry policy the chat path uses.

    429 is not a failure, it is "later": Retry-After is honoured when the header
    is present and an exponential backoff stands in when it is not. 5xx retries
    for the same reason. Other 4xx do not - a bad key or a malformed body fails
    identically three times, and retrying only delays the message.
    """
    result = EmbedResult(model=model)
    started = time.monotonic()
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        # OpenRouter attributes usage to the app that made the call.
        "HTTP-Referer": settings.app_url,
        "X-Title": settings.app_title,
    }

    with httpx.Client(timeout=settings.timeout_seconds) as client:
        for start in range(0, len(texts), BATCH):
            batch = texts[start:start + BATCH]
            body = {"model": model, "input": batch}

            for attempt in range(settings.max_retries):
                response = client.post(
                    f"{settings.base_url}/embeddings", headers=headers, json=body)
                if response.status_code == 200:
                    break
                retryable = response.status_code == 429 or response.status_code >= 500
                if not retryable or attempt == settings.max_retries - 1:
                    raise RuntimeError(
                        f"{model} embeddings failed {response.status_code}: "
                        f"{response.text[:200]}")
                wait = _retry_after(response) or 2.0 ** attempt
                time.sleep(wait)

            payload = response.json()
            # The API promises order but says so only in prose, and a reordered
            # batch would mis-assign every vector in it silently. Sorting by the
            # index the response carries costs nothing and removes the promise.
            data = sorted(payload["data"], key=lambda row: row.get("index", 0))
            result.vectors.extend(row["embedding"] for row in data)
            usage = payload.get("usage") or {}
            result.tokens += usage.get("prompt_tokens", 0)
            result.cost_usd += usage.get("cost", 0.0)
            result.requests += 1

    result.latency_ms = round((time.monotonic() - started) * 1000)

    if len(result.vectors) != len(texts):
        raise RuntimeError(f"{model} returned {len(result.vectors)} vectors "
                           f"for {len(texts)} texts")
    expected = DIMENSIONS.get(model)
    if expected and result.dims != expected:
        raise RuntimeError(f"{model} returned {result.dims} dims, expected "
                           f"{expected} - the index would compare against "
                           f"vectors of a different width")
    return result


def _retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    try:
        return float(raw) if raw else None
    except ValueError:
        return None
