"""Run the classifier over a ticket set and write the raw run to data/runs/.

    python scripts/triage.py --set dev --limit 10
    python scripts/triage.py --set dev                      # all 50
    python scripts/triage.py --set golden --model openai/gpt-5-nano

Scoring lives in eval/score.py. This script only calls the model and records
what came back, including the failures - a run file with 3 errors in it is the
evidence for the failure-handling section, so nothing is dropped here.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# One implementation of the percentile, in the module that owns the metrics: two
# copies of it is how one of them stays wrong after the other is fixed.
sys.path.insert(0, os.path.join(ROOT, "eval"))
from score import (compare_to_console, markdown, percentile,          # noqa: E402
                   report_to_console, score)
from app import llm                                                   # noqa: E402
from app.cache import Cache                                           # noqa: E402
from app.config import MODEL_PROVIDERS, load                           # noqa: E402
from app.llm import classify, render                                  # noqa: E402
from app.split import SPLIT_VERSION, classify_split, split_hash       # noqa: E402


def slug(model: str) -> str:
    return model.replace("/", "-").replace(":", "-")


def free_path(path: str) -> str:
    """Never overwrite a run. The first dev run of v1 was lost to a second run
    under the same name, and it was the only record of a real truncated-JSON
    failure - the kind of evidence the report is built from."""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{stem}__{n}{ext}"):
        n += 1
    return f"{stem}__{n}{ext}"


def record(result) -> dict:
    row = asdict(result)
    row["triage"] = result.triage.model_dump(mode="json") if result.triage else None
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", default="dev",
                        choices=["dev", "golden", "golden2"])
    parser.add_argument("--limit", type=int, default=0, help="0 = the whole set")
    parser.add_argument("--model", default=None, help="overrides the prompt's model")
    parser.add_argument("--prompt", default=None, help="prompt version, e.g. v2")
    parser.add_argument("--workers", type=int, default=4,
                        help="parallel calls; keep low enough not to be rate limited")
    parser.add_argument("--arch", default="single",
                        choices=["single", "split-parallel", "split-staged"],
                        help="single is one call deciding all three fields; the "
                             "split modes give each field its own agent and are "
                             "an experiment, not the default")
    parser.add_argument("--cache", action="store_true",
                        help="reuse answers for identical prompt+model+ticket; "
                             "never use it when measuring spread or cost")
    parser.add_argument("--seed", type=int, default=None,
                        help="best-effort determinism; recorded in the run file")
    parser.add_argument("--out", default=None)
    parser.add_argument("--no-score", action="store_true",
                        help="save the predictions and stop. Only useful if the "
                             "labels are being changed underneath you - the run "
                             "file keeps every prediction, so eval/score.py can "
                             "score it later for free, as many times as needed")
    parser.add_argument("--compare", default=None,
                        help="an earlier run file: also print which tickets "
                             "flipped category, which an accuracy that held "
                             "while half the answers changed will not show")
    args = parser.parse_args()

    started_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    settings = load(args.prompt)
    prompt = settings.prompt
    if args.seed is not None:
        prompt = prompt.model_copy(update={"seed": args.seed})
    model = args.model or prompt.model

    path = os.path.join(ROOT, "data", "tickets", f"{args.set}.json")
    with open(path, encoding="utf-8") as handle:
        tickets = json.load(handle)
    # A partial run is not a measurement - see the output path below.
    smoke = bool(args.limit) and args.limit < len(tickets)
    if args.limit:
        tickets = tickets[:args.limit]

    if args.arch == "single":
        label = f"prompt {prompt.version} ({len(render(prompt)):,} chars)"
    else:
        label = f"prompts split/{SPLIT_VERSION} (3 agents, {split_hash()})"
    # "temp 0.0" was printed for months while gpt-5-mini silently ignored it -
    # none of its endpoints supports temperature. The header now says which
    # parameters the model cannot receive, so the claim matches the request.
    ignored = llm.dropped_params(model, prompt)
    print(f"arch {args.arch} | set {args.set}: {len(tickets)} tickets | {label}"
          f" | temp {prompt.temperature}, {prompt.response_format}"
          f" | model {model} | {args.workers} workers")
    if ignored:
        print(f"  NOT SUPPORTED by this model, so not sent: "
              f"{', '.join(ignored)}")
    pin = MODEL_PROVIDERS.get(model) if settings.pin_providers else None
    if pin:
        print(f"  endpoint pinned to {', '.join(pin)}, no fallbacks")

    cache = Cache(settings.cache_path) if args.cache else None
    if args.arch == "single":
        def run_one(ticket):
            return classify(ticket, settings, model=model, prompt=prompt,
                            cache=cache)
    else:
        mode = args.arch.split("-", 1)[1]
        # The split modes already use three threads per ticket, so the outer
        # pool is narrowed to keep the total near the same concurrency.
        args.workers = max(1, args.workers // 2)

        def run_one(ticket):
            return classify_split(ticket, settings, model=model, prompt=prompt,
                                  mode=mode)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(run_one, tickets))

    for result in results:
        if result.ok:
            triage = result.triage
            print(f"  {result.ticket_id:18} {triage.category.value:22} "
                  f"P{triage.priority.value} {triage.next_step.value:22} "
                  f"conf {triage.confidence:.2f}  {result.latency_ms:>5}ms"
                  f"{'  REPAIRED' if result.repaired else ''}")
        else:
            print(f"  {result.ticket_id:18} FAILED  attempts={result.attempts}  "
                  f"{result.error}")

    ok = [r for r in results if r.ok]
    cost = sum(r.cost_usd for r in results)
    latencies = [r.latency_ms for r in results]
    per_ticket = cost / len(results) if results else 0.0
    print(f"\nok {len(ok)}/{len(results)}  repaired {sum(r.repaired for r in ok)}  "
          f"median {percentile(latencies, 0.50)}ms  "
          f"p95 {percentile(latencies, 0.95)}ms  "
          f"max {max(latencies) if latencies else 0}ms")
    print(f"cost ${cost:.5f} for {len(results)} tickets = ${per_ticket:.5f}/ticket "
          f"-> ${per_ticket * 10_000:.2f} per 10k")
    # The provider's own prompt cache, which is not ours and needs no
    # invalidation: it keys on the literal prefix, so it expires by itself the
    # moment the prompt changes. Printed because it moves the cost by ~57% and
    # would otherwise look like noise in the $/10k column.
    served = sum(r.cached_input_tokens for r in results)
    total_in = sum(r.input_tokens for r in results)
    thinking = sum(r.reasoning_tokens for r in results)
    if total_in:
        print(f"prompt cache: {served:,} of {total_in:,} input tokens served from "
              f"the provider cache ({served / total_in:.0%})"
              + (f" | thinking: {thinking:,} tokens "
                 f"({thinking / max(1, sum(r.output_tokens for r in results)):.0%} "
                 f"of output)" if thinking else ""))
    if cache is not None:
        stats = cache.stats()
        print(f"cache {stats['hits']} hits / {stats['misses']} misses "
              f"({stats['hit_rate']:.0%}), {stats['stored']} entries stored")

    # A partial run is not a run. A 2-ticket smoke of the split architecture once
    # landed under the full run's name, and the ledger averaged it together with a
    # 50-ticket run - 64% +- 20% on two numbers that never belonged in one cell.
    # free_path() protects against overwriting, not against a smoke file that
    # LOOKS like a measurement, so partial runs go somewhere the aggregate does
    # not read from.
    out = args.out or os.path.join(
        settings.runs_dir,
        "_smoke" if smoke else "",
        f"{'_smoke%d__' % args.limit if smoke else ''}"
        f"{args.set}__"
        f"{prompt.version if args.arch == 'single' else SPLIT_VERSION}"
        f"{'' if args.arch == 'single' else '__' + args.arch.replace('-', '')}"
        f"{'__seed%d' % prompt.seed if prompt.seed is not None else ''}"
        f"__{slug(model)}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    out = free_path(out)
    payload = {
        # Everything needed to say what produced these numbers. A run file that
        # does not name its prompt version and model cannot be compared with
        # another one later.
        "source": "triage",
        "reasoning_effort": prompt.reasoning_effort,
        "set": args.set,
        "started_at": started_at,
        "prompt_version": prompt.version if args.arch == "single"
                          else f"{SPLIT_VERSION}-{args.arch}",
        "architecture": args.arch,
        # Pinned and load-balanced runs are not comparable: the endpoints differ
        # in price, in uptime and in whether they implement the schema at all.
        "pinned_endpoint": (MODEL_PROVIDERS.get(model)
                            if settings.pin_providers else None),
        "model": model,
        "temperature": prompt.temperature,
        "response_format": prompt.response_format,
        "seed": prompt.seed,
        "cache_hits": sum(r.cache_hit for r in results),
        # The version NAME is not enough. A .txt edited in place after a run
        # leaves two different prompts claiming to be v2, and the older numbers
        # become unfalsifiable. The hash is of the RENDERED system prompt, so it
        # also moves when the taxonomy behind a placeholder changes.
        "prompt_sha256": (hashlib.sha256(render(prompt).encode("utf-8")).hexdigest()[:16]
                          if args.arch == "single" else split_hash()),
        "max_output_tokens": prompt.max_output_tokens,
        "tickets": len(results),
        "cost_usd": round(cost, 6),
        "results": [record(r) for r in results],
    }
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(f"wrote {os.path.relpath(out, ROOT)}")

    # Score it here. It costs nothing - no API call, no network, milliseconds -
    # and every set this script accepts is fully labelled. Leaving it to a
    # second command meant retyping a filename the line above had just printed,
    # and getting the run suffix wrong scores an OLDER run and prints a number
    # that looks entirely reasonable.
    if not args.no_score:
        report = score(payload)
        stem = os.path.splitext(os.path.basename(out))[0]
        results_dir = os.path.join(ROOT, "eval", "results")
        os.makedirs(results_dir, exist_ok=True)
        with open(os.path.join(results_dir, f"{stem}.json"), "w",
                  encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        with open(os.path.join(results_dir, f"{stem}.md"), "w",
                  encoding="utf-8") as handle:
            handle.write(markdown(report))
        print()
        report_to_console(report)
        if args.compare:
            compare_to_console(report, args.compare)
        print(f"wrote eval/results/{stem}.md and .json")


if __name__ == "__main__":
    main()
