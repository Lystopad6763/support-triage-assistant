"""Ask the catalogue which parameters each model's endpoints actually support.

    python scripts/probe_models.py            # rewrite data/model_params.json

WHY THIS FILE EXISTS
    OpenRouter serves one model id through every provider that hosts it - ten of
    them for qwen3-235b-a22b-2507 - and silently drops any parameter the chosen
    endpoint does not support. We sent "temperature": 0 to gpt-5-mini for the
    whole of the prompt work. Not one of its endpoints supports temperature:

        include_reasoning, max_tokens, reasoning, reasoning_effort,
        response_format, seed, structured_outputs, tool_choice, tools

    so the prompt was never tuned at temperature 0 at all, and the run-to-run
    spread we kept reporting was the model's own default sampling. The same is
    true of claude-sonnet-5. Nothing failed, nothing warned, and every artifact
    said "temp 0.0".

    The same silence produced a second bug: provider.require_parameters, which
    routes only to endpoints supporting everything in the request, answered 404
    "no endpoints found" for gpt-5-mini, gpt-5-nano and claude-sonnet-5. It was
    right - we were asking for temperature, which none of them has. Dropping that
    one field makes require_parameters work, and with it the schema is guaranteed
    by routing rather than repaired afterwards.

WHAT IS WRITTEN
    For each model, the intersection and the union of supported_parameters over
    its endpoints, plus the endpoint count and how many of them declare
    structured_outputs. The INTERSECTION is what app/llm.py sends: a parameter
    only some endpoints honour is a parameter whose effect depends on load
    balancing, which is worse than not sending it - the numbers would be a blend
    of two settings with no way to tell which call got which.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.config import MODEL_PROVIDERS, PROMPTS, load                 # noqa: E402

OUT = os.path.join(ROOT, "data", "model_params.json")
CATALOGUE = "https://openrouter.ai/api/v1/models/{}/endpoints"


def probe(model: str) -> dict:
    response = httpx.get(CATALOGUE.format(model), timeout=30)
    response.raise_for_status()
    payload = response.json()["data"]
    endpoints = payload["endpoints"]
    stamp = payload.get("created")
    created = (dt.datetime.fromtimestamp(stamp).date().isoformat()
               if isinstance(stamp, (int, float)) else None)
    pins = MODEL_PROVIDERS.get(model) or []
    pinned = None
    # Exact tag first, prefix only as a fallback. Matching by prefix alone made
    # "openai" resolve to "openai/flex" - a different service tier at 45% of the
    # price - and reported that as the price of our pin. Verified live: only
    # ["openai"] is served with service_tier "default", ["openai/flex"] with
    # "flex", so the exact tag is the pin and the prefix is a different product.
    for endpoint in endpoints:
        tag = str(endpoint.get("tag") or "")
        if tag in pins:
            price = endpoint.get("pricing") or {}
            pinned = {"tag": tag,
                      "in_per_m": round(float(price.get("prompt") or 0) * 1e6, 4),
                      "out_per_m": round(float(price.get("completion") or 0) * 1e6, 4)}
            break
    sets = [set(e.get("supported_parameters") or []) for e in endpoints]
    both = sorted(set.intersection(*sets)) if sets else []
    either = sorted(set.union(*sets)) if sets else []
    return {
        "endpoints": len(endpoints),
        # No dated snapshot exists for most of these ids and the response body
        # echoes the alias rather than the version that served it, so there is no
        # fingerprint of a silent model swap anywhere in the API. This date is the
        # only free signal: re-probe, and a changed value means the catalogue
        # entry moved. The real detector is a canary - the same tickets at
        # temperature 0 on a model whose output is bit-stable - which is possible
        # only because gpt-4.1-mini scored 82% five runs in a row.
        "created": created,
        "providers": sorted({e.get("provider_name", "?") for e in endpoints}),
        "structured_outputs": sum("structured_outputs" in s for s in sets),
        "max_completion_tokens": sorted(
            {e.get("max_completion_tokens") for e in endpoints
             if e.get("max_completion_tokens")}),
        "all": both,
        "any": either,
        # The prices in app/config.py are comments typed by hand on 2026-09-20.
        # Cost comes back per call so nothing depends on them, but a stale number
        # in the repo is still a claim, and this makes it checkable. Per 1M tokens.
        "price_in_per_m": sorted({round(float(e["pricing"]["prompt"]) * 1e6, 4)
                                  for e in endpoints if (e.get("pricing") or {}).get("prompt")}),
        "price_out_per_m": sorted({round(float(e["pricing"]["completion"]) * 1e6, 4)
                                   for e in endpoints if (e.get("pricing") or {}).get("completion")}),
        # The only price that is ours: the one charged by the endpoint we pinned.
        # gemini-3.1-flash-lite spans 0.125-0.45 in and 0.75-2.7 out across its
        # eight endpoints, a 3.6x spread inside one model id, so "the price of the
        # model" is not a thing that exists until routing is fixed.
        "price_at_pin": pinned,
    }


def main() -> None:
    settings = load()
    models = sorted({*settings.benchmark_models,
                     *(p.model for p in PROMPTS.values())})
    out = {"probed_at": dt.datetime.now().isoformat(timespec="seconds"),
           "models": {}}
    for model in models:
        try:
            info = probe(model)
        except Exception as exc:                                   # noqa: BLE001
            print(f"  {model:32} FAILED {type(exc).__name__}: {exc}")
            continue
        out["models"][model] = info
        missing = [p for p in ("temperature", "seed", "max_tokens")
                   if p not in info["all"]]
        print(f"  {model:32} {info['endpoints']:2} endpoints, "
              f"{info['structured_outputs']} with structured_outputs"
              + (f"  | NOT supported everywhere: {', '.join(missing)}"
                 if missing else ""))
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    print(f"\nwrote {os.path.relpath(OUT, ROOT)} for {len(out['models'])} models")


if __name__ == "__main__":
    main()
