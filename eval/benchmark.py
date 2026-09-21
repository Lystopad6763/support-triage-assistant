"""Five models on the golden set, under TWO prompts, several runs each.

    python eval/benchmark.py                      # v1 and v8, 2 runs each
    python eval/benchmark.py --repeats 1 --prompts v8
    python eval/benchmark.py --prompts v8 --repeats 1 --limit 4 --model-workers 8

WHAT THE LOG PRINTS AND WHY IT IS NOT DECORATION
    Eight models will sit still for minutes at a time, and two candidates had to
    be dropped for stalling - one at 8.9 minutes per ticket. A per-cell line
    cannot tell a slow provider from a wedged process, so every reply is printed
    as it lands, with attempts and repairs, and a WAITING line names the cells in
    flight whenever the log has been silent. See the Progress class.

WHY TWO PROMPTS
    The working prompt was iterated against gpt-5-mini, so a benchmark that uses
    only that prompt answers "which model best runs a prompt tuned for
    gpt-5-mini", not "which model is best at this task". v1 is the control: it is
    the bare taxonomy, written before any model's errors were seen. v8 is the
    frozen prompt - the last version whose gain exceeded the run-to-run spread
    (category 84% +-3 against 78% +-5, macro F1 over the four classes with real
    support 0.79 against 0.72). Its one measured regression, escalation recall
    83% -> 70%, is deliberately not fixed with another sentence: the escalation
    triggers are facts stated in the text, so they belong in a deterministic gate
    that cannot be talked out of them.

    If the ranking is the same under both, the prompt is not choosing the winner.
    If a model wins only under v5, the bias is real and this table measures it.

WHY REASONING IS "VENDOR DEFAULT" BY DEFAULT HERE
    reasoning_effort is not a portable setting. On the gpt-5 family "low" is a
    small internal budget; on Claude the same word maps to extended thinking, and
    a probe measured 2,611 output tokens against 109 without it - five times the
    cost and ten times the latency for the same answer.

    But omitting the parameter is NOT neutral either, and an earlier version of
    this file claimed it was. Not sending it means each vendor's own default, and
    those differ: in one smoke run gpt-5-nano spent 3,175 output tokens thinking
    and gpt-5-mini 834, while Claude and Gemini spent 130-180, because extended
    thinking is off unless asked for. So --reasoning off means "vendor defaults",
    which is a legitimate comparison as long as it is labelled as one.

    There is no single off switch either: reasoning {"effort": "none"} is refused
    by gpt-5 with 400 "Reasoning is mandatory for this endpoint". "minimal" is the
    floor there, and it is cheap - 116 output tokens against 834, 2.9s against
    12.6s - which makes it a round-two setting rather than a neutral baseline.

WHY SEVERAL RUNS
    temperature 0 is not deterministic here and seed does not fix it: six runs of
    v5 on dev spread over 68-80% on category (sd 4). A single run per cell cannot
    separate two models that are less than ~8 points apart, so each cell is run
    more than once and reported as a mean.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import statistics as st
from collections import Counter
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "eval"))
from app.config import MODEL_OVERRIDES, MODEL_PROVIDERS, load         # noqa: E402
from app.taxonomy import Category                                     # noqa: E402
from scripts.triage import free_path, record, slug                    # noqa: E402
from app import llm                                                   # noqa: E402
from app.llm import classify, render                                  # noqa: E402
from disagreement import analyse                                      # noqa: E402
from score import percentile, score                                   # noqa: E402

FIELDS = ("category_accuracy", "priority_accuracy", "next_step_accuracy",
          "all_three_accuracy", "evidence_verbatim_rate")


class Progress:
    """Say what is happening while it happens, not after.

    The first version printed one line per finished cell, which is useless in the
    one situation that matters: a benchmark of eight models WILL sit still for
    minutes, and the difference between "a slow provider is thinking" and "the
    process is wedged" was invisible. Two models had to be dropped for stalling
    (8.9 minutes per ticket on one), so the reporter is part of the measurement,
    not decoration.

    Three things are printed that a per-cell line cannot carry:
      - every ticket as it lands, with attempts and repairs, so a provider that
        answers only after a retry is visible rather than averaged away;
      - a WAITING line whenever nothing has been printed for a while, naming each
        cell in flight and its count, which is what tells a stall from slowness;
      - the elapsed wall clock on every line, because the useful question after a
        crash is "how far in", and a timestamp answers it.

    Every write goes through one lock: with models running concurrently, unlocked
    prints from several threads interleave mid-line and the log becomes unreadable
    exactly when it is needed.
    """

    def __init__(self, per_ticket: bool = True, quiet_after: float = 20.0):
        self.per_ticket = per_ticket
        self.quiet_after = quiet_after
        self.lock = threading.Lock()
        self.started = time.monotonic()
        self.last_event = self.started      # last reply or cell boundary
        self.last_line = self.started       # last line printed, heartbeats too
        self.inflight: dict[str, list[int]] = {}

    def line(self, text: str, event: bool = True) -> None:
        with self.lock:
            print(f"[{time.monotonic() - self.started:7.1f}s] {text}", flush=True)
            self.last_line = time.monotonic()
            if event:
                self.last_event = self.last_line

    def open_cell(self, tag: str, total: int) -> None:
        with self.lock:
            self.inflight[tag] = [0, total]
        self.line(f"START  {tag}  {total} tickets")

    def close_cell(self, tag: str) -> None:
        with self.lock:
            self.inflight.pop(tag, None)

    def tick(self, tag: str, ticket: dict, result) -> None:
        with self.lock:
            counter = self.inflight.get(tag)
            if counter:
                counter[0] += 1
            done, total = counter if counter else (0, 0)
        if not self.per_ticket:
            return
        marks = []
        if result.attempts > 1:
            marks.append(f"attempt {result.attempts}")
        if result.repaired:
            marks.append("REPAIRED")
        if result.triage is not None:
            body = (f"ok    {result.triage.category.value:22}"
                    f"P{result.triage.priority.value} "
                    f"{result.triage.next_step.value}")
        else:
            body = f"FAIL  {result.error}"
        # One model id is served by up to ten providers and OpenRouter picks one
        # per request, so the endpoint belongs on the same line as the latency it
        # produced. Without it, "qwen was slow" is a claim about nothing.
        if result.provider:
            body += f"  via {result.provider}"
        self.line(f"       {tag}  {done}/{total}  "
                  f"{ticket.get('ticket_id', '?'):18}{body}  "
                  f"{result.latency_ms}ms" + (f"  [{', '.join(marks)}]" if marks else ""))

    def watch(self) -> None:
        """Daemon loop: break the silence so a stall is not mistaken for work.

        The age reported is the age of the last REPLY, not of the last line
        printed - a heartbeat that reset its own clock would report the same five
        seconds forever and hide how long a provider has actually been quiet.
        """
        while True:
            time.sleep(5)
            with self.lock:
                quiet = time.monotonic() - self.last_event
                since_line = time.monotonic() - self.last_line
                snapshot = [(tag, d, n) for tag, (d, n) in self.inflight.items()]
            if quiet >= self.quiet_after and since_line >= 5 and snapshot:
                self.line(f"WAITING  {quiet:.0f}s since the last reply | "
                          + " | ".join(f"{tag} {d}/{n}"
                                       for tag, d, n in snapshot), event=False)


def cell_from_run(run: dict) -> dict:
    """Score one run and enrich it into a benchmark cell.

    Takes the run DICT, not the Result objects, so the same code produces a cell
    from a run measured a second ago and from one loaded off disk. That is what
    makes --rescore possible: when a label turns out to be wrong the whole table
    is rebuilt from saved runs for free, and the only thing that changed is the
    yardstick. A second implementation for the file path would drift from this one
    the first time a metric was added to either.
    """
    rows = run["results"]
    report = score(run)
    summary = report["summary"]
    latencies = [r["latency_ms"] for r in rows]
    summary["latency_p50"] = percentile(latencies, 0.50)
    summary["latency_p95"] = percentile(latencies, 0.95)
    # The single worst ticket, named for what it is. p99 on 50 tickets IS this
    # number dressed up as a percentile, and our own 60-second ticket budget
    # truncates the distribution anyway - anything slower is a failure, not a
    # latency, and it is counted in hard_failures.
    summary["latency_max"] = max(latencies) if latencies else 0
    summary["repaired"] = sum(bool(r.get("repaired")) for r in rows)
    # Tokens are reported next to cost because they are the part that does not
    # move when the catalogue price changes.
    summary["input_tokens"] = st.mean([r["input_tokens"] for r in rows])
    summary["output_tokens"] = st.mean([r["output_tokens"] for r in rows])
    # Thinking tokens are billed as output and invisible in the answer: gpt-5-nano
    # spent 2,987 of them per ticket against gemini's 0. Cached input tokens are
    # the other half of the cost story - a warm prefix cut one call from $0.00092
    # to $0.00039, which is why five identical runs cost $4.87 to $6.14 per 10k.
    summary["reasoning_tokens"] = st.mean([r.get("reasoning_tokens") or 0
                                           for r in rows])
    summary["cached_input_tokens"] = st.mean([r.get("cached_input_tokens") or 0
                                              for r in rows])
    summary["confusion"] = report["confusion"]
    served: dict[str, int] = {}
    for row in rows:
        name = row.get("provider") or "(unknown)"
        served[name] = served.get(name, 0) + 1
    summary["providers"] = served
    summary["pinned_endpoint"] = run.get("pinned_endpoint")
    # The language cut is the reason this benchmark has ten models in it: a
    # quarter of the set is not English and the average hides that completely.
    language = (report.get("buckets") or {}).get("language", {})
    summary["by_language"] = {k: v["category"] for k, v in language.items()}
    return summary


def rescore(set_name: str) -> dict[tuple[str, str], list[dict]]:
    """Rebuild every cell from the runs on disk, without a single API call."""
    table: dict[tuple[str, str], list[dict]] = {}
    pattern = os.path.join(ROOT, "data", "runs", f"{set_name}__*.json")
    for path in sorted(glob.glob(pattern)):
        with open(path, encoding="utf-8") as handle:
            run = json.load(handle)
        if len(run.get("results", [])) < 50:
            continue
        # Runs written before "source" existed: the benchmark never recorded
        # started_at and triage always did, so absence of both is a benchmark run.
        source = run.get("source") or ("benchmark" if not run.get("started_at")
                                       else "triage")
        if source != "benchmark":
            continue
        cell = cell_from_run(run)
        # Untagged means the run predates the "source" field, so it also predates
        # the parameter filtering and the ticket-level deadline. Two such runs of
        # gpt-4o-mini were silently averaged in with two fresh ones, making that
        # one cell a 4-run mean where the other 19 were 2-run - visible only as
        # "OpenAI x200" in the served-by column of a 100-ticket row.
        cell["provenance"] = "tagged" if run.get("source") else "untagged"
        cell["run_file"] = os.path.relpath(path, ROOT)
        cell["prompt_sha256"] = run.get("prompt_sha256") or cell.get("prompt_sha256")
        cell.setdefault("settings",
                        {"reasoning_effort": run.get("reasoning_effort"),
                         "temperature": run.get("temperature")})
        cell["measured_at"] = run.get("started_at") or cell.get("measured_at")
        table.setdefault((run["prompt_version"], run["model"]), []).append(cell)

    # Which prompt text actually produced each run, against the prompt that
    # version renders to NOW. A run measured under a different taxonomy is not
    # wrong, it is answering a different question, and the report has to say so.
    current = {}
    for key, cells in table.items():
        version = key[0]
        if version not in current:
            try:
                current[version] = hashlib.sha256(
                    render(load(version).prompt).encode("utf-8")).hexdigest()[:16]
            except Exception:                                      # noqa: BLE001
                current[version] = None
        for cell in cells:
            saved = cell.get("prompt_sha256")
            cell["prompt_current"] = (
                "same" if saved and saved == current[version]
                else ("unknown" if not saved else "DIFFERENT"))

    # One cell, one provenance. An untagged run is a fallback for a cell that has
    # nothing better, never an addition to one that does.
    for key, cells in table.items():
        tagged = [c for c in cells if c["provenance"] == "tagged"]
        if tagged and len(tagged) != len(cells):
            dropped = [c["run_file"] for c in cells if c["provenance"] == "untagged"]
            print(f"       {key[0]} {key[1]}: ignoring {len(dropped)} run(s) from "
                  f"before provenance was recorded, {len(tagged)} fresh run(s) kept")
            for name in dropped:
                print(f"         - {name}")
            table[key] = tagged
    return table


def one_run(tickets: list[dict], settings, prompt, model: str, workers: int,
            set_name: str, progress: Progress, tag: str,
            smoke: bool = False) -> dict:
    def work(ticket: dict):
        # Without this hook a ticket that times out twice prints nothing for two
        # minutes and then one line, which is exactly the silence the WAITING
        # heartbeat was added to explain.
        def notify(message: str) -> None:
            progress.line(f"       {tag}  ..   "
                          f"{ticket.get('ticket_id', '?'):18}{message}")

        result = classify(ticket, settings, model=model, prompt=prompt,
                          notify=notify)
        progress.tick(tag, ticket, result)
        return result

    progress.open_cell(tag, len(tickets))
    try:
        # pool.map keeps the ticket order in the run file while the log prints in
        # completion order - the file is for scoring, the log is for watching.
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(work, tickets))
    finally:
        progress.close_cell(tag)
    run = {
        # Who wrote this run, and under which generation mode. --rescore rebuilds
        # the benchmark table from saved runs and must take ONLY benchmark runs:
        # a triage run of the same model and prompt carries the prompt's own
        # reasoning_effort, while the benchmark sends none, and mixing them put
        # gemini-2.5-flash-lite in one cell at 181 output tokens and at 2,275.
        "source": "benchmark",
        "reasoning_effort": prompt.reasoning_effort,
        "set": set_name,
        "prompt_version": prompt.version,
        # The hash of the text ACTUALLY SENT, taken from the prompt object this
        # run used, not copied out of a summary that does not have it yet.
        "prompt_sha256": hashlib.sha256(
            render(prompt).encode("utf-8")).hexdigest()[:16],
        "model": model,
        "tickets": len(results),
        "cost_usd": sum(r.cost_usd for r in results),
        "pinned_endpoint": (MODEL_PROVIDERS.get(model)
                            if settings.pin_providers else None),
        "results": [record(r) for r in results],
    }
    summary = cell_from_run(run)

    # KEEP THE PREDICTIONS. Scoring them and dropping them cost nothing until the
    # first time a label turned out to be wrong: rescoring is free from a run
    # file and costs another $4 and 40 minutes from nothing. The per-ticket rows
    # are also the only input eval/disagreement.py has - ten models reading the
    # same golden ticket is the strongest label audit available, and it exists
    # only if these files do.
    directory = (os.path.join(settings.runs_dir, "_smoke") if smoke
                 else str(settings.runs_dir))
    os.makedirs(directory, exist_ok=True)
    path = free_path(os.path.join(
        directory,
        f"{'_smoke%d__' % len(tickets) if smoke else ''}"
        f"{set_name}__{prompt.version}__{slug(model)}.json"))
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(dict(run, architecture="single"), handle,
                  ensure_ascii=False, indent=2)
    summary["run_file"] = os.path.relpath(path, ROOT)
    return summary


def providers_of(cell: dict) -> str:
    """The endpoints that served one cell, most used first. More than one name
    here means the cell's latency is a blend of several machines."""
    served = cell.get("providers") or {}
    return ", ".join(f"{name} x{count}" for name, count
                     in sorted(served.items(), key=lambda kv: -kv[1])) or "-"


def maybe(cells: list[dict], *fields: str, fmt: str = "{:.2f}", sep: str = "/") -> str:
    """Format metrics that may predate the cells being formatted.

    A cell measured before a metric existed has no value for it, and agg()
    returns 0.0 there - which in a table reads as "zero precision" rather than
    "not measured". A dash is the truth.
    """
    if not any(field in c and c[field] is not None for c in cells for field in fields):
        return "-"
    return sep.join(fmt.format(agg(cells, field)[0]) for field in fields)


def cell_line(cell: dict) -> str:
    """One finished run in one line, readable even when nothing was scored - a
    cell where every ticket failed used to crash the summary on a None macro F1,
    which was the moment the log was most needed."""
    if not cell.get("scored"):
        return (f"NOTHING SCORED  fail {cell['hard_failures']}  "
                f"${cell['cost_per_10k']:.2f}/10k")
    f1 = cell.get("macro_f1")
    return (f"cat {cell['category_accuracy']:.0%}  "
            f"F1 {'-' if f1 is None else format(f1, '.2f')}  "
            f"all3 {cell['all_three_accuracy']:.0%}  "
            f"fail {cell['hard_failures']}  rep {cell['repaired']}  "
            f"p50 {cell['latency_p50']}ms  p95 {cell['latency_p95']}ms  "
            f"tok {int(cell['input_tokens'])}/{int(cell['output_tokens'])}  "
            f"${cell['cost_per_10k']:.2f}/10k  "
            f"via {providers_of(cell)}")


def agg(cells: list[dict], field: str) -> tuple[float, float]:
    # A cell that crashed outright has no runs at all, and it still has to be
    # sortable: st.mean([]) raises, which would lose the whole table to one
    # broken model id.
    values = [c[field] for c in cells if c.get(field) is not None]
    if not values:
        return 0.0, 0.0
    return st.mean(values), (st.stdev(values) if len(values) > 1 else 0.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    # golden stays the frozen 50 that every number in the journal refers to.
    # golden2 is those 50 plus 32 supplements that give ten of the eleven
    # categories three or more rows, so macro F1 stops being four coin flips.
    parser.add_argument("--set", default="golden",
                        choices=["golden", "golden2", "dev"])
    parser.add_argument("--prompts", default="v1,v8")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--reasoning", default="off",
                        choices=["off", "inherit", "per-model"],
                        help="off (default) sends no reasoning parameter, the "
                             "only setting that means the same thing to every "
                             "vendor; inherit keeps the prompt's own; per-model "
                             "applies app.config.MODEL_OVERRIDES, which is round "
                             "two - one adaptation per model, same budget each")
    parser.add_argument("--limit", type=int, default=0,
                        help="tickets per run, 0 = the whole set. A few tickets "
                             "across every model is the cheap way to find out "
                             "that an id has moved or a provider rejects the "
                             "schema, before spending the full run")
    parser.add_argument("--models", default=None,
                        help="comma separated; default is the benchmark list")
    parser.add_argument("--model-workers", type=int, default=1,
                        help="models measured at the same time. 1 by default: "
                             "concurrent models share one account rate limit, and "
                             "a 429 served to a model halfway through its cell "
                             "adds backoff to ITS latency, which is the number "
                             "being measured. Raise it for a smoke run, where the "
                             "question is whether every id answers at all and the "
                             "timings do not matter")
    parser.add_argument("--rescore", action="store_true",
                        help="rebuild the report from the run files already on "
                             "disk, with no API calls at all. This is what a label "
                             "fix costs: nothing. Only cells whose per-ticket runs "
                             "were saved can be rebuilt")
    parser.add_argument("--progress", default="ticket",
                        choices=["ticket", "cell"],
                        help="ticket (default) prints every reply as it lands; "
                             "cell prints one line per finished run")
    args = parser.parse_args()

    settings = load()
    models = args.models.split(",") if args.models else list(settings.benchmark_models)
    versions = args.prompts.split(",")

    with open(os.path.join(ROOT, "data", "tickets", f"{args.set}.json"),
              encoding="utf-8") as handle:
        tickets = json.load(handle)
    if args.limit:
        tickets = tickets[:args.limit]

    calls = len(models) * len(versions) * args.repeats * len(tickets)
    print(f"{len(models)} models x {len(versions)} prompts x {args.repeats} runs "
          f"x {len(tickets)} tickets = {calls} calls\n")

    progress = Progress(per_ticket=args.progress == "ticket")
    threading.Thread(target=progress.watch, daemon=True).start()
    table: dict[tuple[str, str], list[dict]] = {}
    if args.rescore:
        table = rescore(args.set)
        if not table:
            sys.exit(f"no saved {args.set} runs to rescore - "
                     f"data/runs/{args.set}__*.json has none with 50 tickets")
        versions = sorted({v for v, _ in table}, key=lambda v: (v != "v1", v))
        known = list(settings.benchmark_models)
        models = [m for m in known + sorted({m for _, m in table} - set(known))
                  if any((v, m) in table for v in versions)]
        progress.line(f"rescoring {sum(len(c) for c in table.values())} saved runs "
                      f"into {len(table)} cells, no API calls")
    progress.line(f"transport: {settings.timeout_seconds}s per socket operation, "
                  f"{settings.timeout_seconds * llm.DEADLINE_FACTOR:.0f}s wall "
                  f"clock per ticket across all attempts, "
                  f"{settings.max_retries} attempts | {args.workers} ticket "
                  f"workers x {args.model_workers} model workers = up to "
                  f"{args.workers * args.model_workers} calls in flight | "
                  f"endpoints {'PINNED to the vendor own service' if settings.pin_providers else 'load balanced by OpenRouter'}")

    for version in (versions if not args.rescore else []):
        prompt = load(version).prompt
        if args.reasoning == "off":
            prompt = prompt.model_copy(update={"reasoning_effort": None})
        rendered_hash = hashlib.sha256(
            render(prompt).encode("utf-8")).hexdigest()[:16]
        progress.line(f"PROMPT {version}  {len(render(prompt)):,} chars  "
                      f"sha {rendered_hash}  temp {prompt.temperature}  "
                      f"{prompt.response_format}  reasoning "
                      f"{prompt.reasoning_effort or 'parameter not sent'}")

        def cell_for(model: str, version=version, prompt=prompt,
                     rendered_hash=rendered_hash) -> tuple[str, list[dict]]:
            per_model = prompt
            if args.reasoning == "per-model" and model in MODEL_OVERRIDES:
                per_model = prompt.model_copy(update=MODEL_OVERRIDES[model])
            cells = []
            for run_index in range(args.repeats):
                tag = f"{version} {model:30} r{run_index + 1}"
                try:
                    cell = one_run(tickets, settings, per_model, model,
                                   args.workers, args.set, progress, tag,
                                   smoke=bool(args.limit))
                except Exception:                                  # noqa: BLE001
                    # One unusable model id must not take the other seven with
                    # it. The traceback is printed in full, because the whole
                    # point of a smoke run is finding out what breaks and where.
                    progress.line("CRASH  " + tag + "\n" + traceback.format_exc())
                    continue
                cell["settings"] = {"reasoning_effort": per_model.reasoning_effort,
                                    "temperature": per_model.temperature}
                cell["prompt_sha256"] = rendered_hash
                cell["measured_at"] = dt.datetime.now().isoformat(timespec="seconds")
                cells.append(cell)
                progress.line(f"DONE   {tag}  {cell_line(cell)}")
                progress.line(f"       {tag}  -> {cell.get('run_file')}")
            return model, cells

        if args.model_workers > 1:
            with ThreadPoolExecutor(max_workers=args.model_workers) as pool:
                finished = list(pool.map(cell_for, models))
        else:
            finished = [cell_for(model) for model in models]
        for model, cells in finished:
            table[(version, model)] = cells

    suffix = f"__smoke{args.limit}" if args.limit else ""
    out = os.path.join(ROOT, "eval", "results", f"benchmark__{args.set}{suffix}")

    # TOP UP, DO NOT CLOBBER. Nine models take 30 minutes and $3; adding a tenth
    # afterwards takes 90 seconds, and writing the report from that one
    # invocation would replace the nine-model table with a one-row one. Cells
    # measured now win; cells measured earlier are kept and carry the date they
    # were measured, because a table that silently blends two runs of different
    # code is worse than two honest tables.
    carried: dict[tuple[str, str], list[dict]] = {}
    if os.path.exists(f"{out}.json"):
        with open(f"{out}.json", encoding="utf-8") as handle:
            for key, cells in json.load(handle).items():
                version, _, name = key.partition("|")
                if (version, name) not in table:
                    carried[(version, name)] = cells
    if carried:
        progress.line(f"carried over {len(carried)} cells from the previous "
                      f"{os.path.basename(out)}.json: "
                      + ", ".join(f"{v} {m}" for v, m in sorted(carried)))
        table = {**carried, **table}
        versions = sorted({v for v, _ in table}, key=lambda v: (v != "v1", v))
        known = list(settings.benchmark_models)
        models = [m for m in known + sorted({m for _, m in table} - set(known))
                  if any((v, m) in table for v in versions)]

    lines = [f"# {len(models)} models on {args.set}, {args.repeats} runs per cell",
             "",
             f"settings mode: **{args.reasoning}**"
             + (" - no reasoning parameter is sent, because \"low\" means a "
                "small budget on gpt-5 and full extended thinking on Claude, "
                "which would compare modes rather than models"
                if args.reasoning == "off" else " - each prompt's own setting"),
             "",
             "Mean over runs; +- is the spread across runs of the same cell, which "
             "is the floor below which two models are not distinguishable.",
             ""]

    # What macro F1 is an average over, stated where the column is read.
    support = Counter(t["label"]["category"] for t in tickets)
    thin = sorted(c for c, k in support.items() if k <= 2)
    core = sorted(c for c, k in support.items() if k >= 3)
    absent = sorted({c.value for c in Category} - set(support))
    lines += [
        f"**What macro F1 averages over.** {len(support)} of {len(Category)} "
        f"categories appear in `{args.set}`: " +
        ", ".join(f"`{c}` x{support[c]}" for c, _ in support.most_common()) + ".",
        "",
        f"- {len(core)} classes carry 3+ rows and are readable: "
        f"{', '.join(f'`{c}`' for c in core) or 'none'}.",
        f"- {len(thin)} classes carry two rows or fewer: "
        f"{', '.join(f'`{c}`' for c in thin) or 'none'}. F1 on those is 0 or 1 "
        "with nothing between, and macro F1 weights each of them the same as a "
        "class with forty rows. The **macro F1** column therefore moves several "
        "points on a single ticket. Read it beside the accuracy column, not "
        "instead of it.",
        f"- {len(absent)} categories never appear at all: "
        f"{', '.join(f'`{c}`' for c in absent) or 'none'}. Nothing in this table "
        "measures them.",
        ""]
    for version in versions:
        lines += [f"## Prompt {version}", "",
                  "| model | served by | category | macro F1 | macro P/R | "
                  "non-latin | all three | esc P/R | evidence | hard fails "
                  "| tokens in/out | thinking | cached in | p50 | p95 | $/10k |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        ranked = sorted(models,
                        key=lambda m: -agg(table.get((version, m)) or [],
                                           "category_accuracy")[0])
        for model in ranked:
            cells = table.get((version, model))
            if not cells:
                lines.append(f"| {model} | - | *not measured under {version}* "
                             f"| - | - | - | - | - | - | - | - | - | - |")
                continue
            if all(c["scored"] == 0 for c in cells):
                lines.append(f"| {model} | - | **did not answer** | - | - | - "
                             f"| - | - | - | {sum(c['hard_failures'] for c in cells)} "
                             f"| - | - | - | - | - | - |")
                continue
            attempted = sum(c["tickets"] for c in cells)
            answered = sum(c["scored"] for c in cells)
            thin = answered < 0.9 * attempted
            cat, cat_sd = agg(cells, "category_accuracy")
            all3, _ = agg(cells, "all_three_accuracy")
            step, _ = agg(cells, "next_step_accuracy")
            ev, _ = agg(cells, "evidence_verbatim_rate")
            macro, _ = agg(cells, "macro_f1")
            nonlatin = [c["by_language"].get("non-latin script")
                        for c in cells if c["by_language"].get("non-latin script") is not None]
            # A cell where every ticket failed has no rows, so it has no
            # escalation numbers either - and printing 0% there would read as
            # "never escalates" rather than "never answered".
            esc = [c["escalation"] for c in cells if c["escalation"]]
            esc_p = st.mean([e["precision"] for e in esc]) if esc else None
            esc_r = st.mean([e["recall"] for e in esc]) if esc else None
            esc_cell = f"{esc_p:.0%}/{esc_r:.0%}" if esc else "-"
            served: dict[str, int] = {}
            for cell in cells:
                for name, count in (cell.get("providers") or {}).items():
                    served[name] = served.get(name, 0) + count
            lines.append(
                f"| {model} "
                f"| {', '.join(f'{k} x{v}' for k, v in sorted(served.items(), key=lambda kv: -kv[1])) or '-'} "
                f"| {cat:.0%} +-{cat_sd:.0%}"
                f"{f' **n={answered}/{attempted}**' if thin else ''} "
                f"| {macro:.2f} "
                f"| {maybe(cells, 'macro_precision', 'macro_recall')} "
                f"| {(st.mean(nonlatin) if nonlatin else 0):.0%} | {all3:.0%} "
                f"| {esc_cell} | {ev:.0%} "
                f"| {sum(c['hard_failures'] for c in cells)} "
                f"| {int(st.mean([c['input_tokens'] for c in cells])):,}/"
                f"{int(st.mean([c['output_tokens'] for c in cells])):,} "
                f"| {maybe(cells, 'reasoning_tokens', fmt='{:,.0f}')} "
                f"| {maybe(cells, 'cached_input_tokens', fmt='{:,.0f}')} "
                f"| {int(st.mean([c['latency_p50'] for c in cells]))}ms "
                f"| {int(st.mean([c['latency_p95'] for c in cells]))}ms "
                f"| ${st.mean([c['cost_per_10k'] for c in cells]):.2f} |")
        lines.append("")

    if len(versions) > 1:
        lines += ["## Did the prompt choose the winner?", ""]
        for version in versions:
            order = sorted([m for m in models
                            if sum(c["scored"] for c in table.get((version, m)) or [])
                            >= 0.9 * sum(c["tickets"] for c in table.get((version, m)) or [])],
                           key=lambda m: -agg(table.get((version, m)) or [],
                                              "category_accuracy")[0])
            lines.append(f"- **{version}**: " + " > ".join(
                f"{m} ({agg(table.get((version, m)) or [], 'category_accuracy')[0]:.0%})"
                for m in order))
        lines += ["",
                  "Same order under both prompts means the prompt is not deciding "
                  "the ranking. A model that only leads under the tuned prompt is "
                  "evidence of the bias, and the gap is its size. A model that "
                  "answered fewer than 90% of its tickets is left out of these two "
                  "orderings and carries **n=answered/attempted** in the table "
                  "above: its accuracy is measured on whatever survived, which is "
                  "not the same test the others took.", ""]

    stale = sorted({(v, m, c.get("prompt_current"))
                    for (v, m), cells in table.items() for c in cells
                    if c.get("prompt_current") in ("unknown", "DIFFERENT")})
    if stale:
        versions = sorted({v for v, _, _ in stale})
        lines += ["## These rows were measured under a different prompt", "",
                  "`prompt_sha256` on the saved run does not match what "
                  f"{', '.join(versions)} renders to now. The taxonomy, the "
                  "rules or the wording has moved since, so the models that "
                  "produced these answers were shown a different question. "
                  "Rescoring them is honest about the LABELS and silent about "
                  "the PROMPT, which is why this block exists.",
                  "", "| cell | saved hash |", "|---|---|"]
        for version, model, state in stale:
            word = ("not recorded - the run predates the fix that writes it"
                    if state == "unknown" else "differs from the current text")
            lines.append(f"| {version} {model} | {word} |")
        lines.append("")

    if carried:
        # Say it in the report, not only in the terminal: whoever reads the table
        # later has to be able to see that some rows are older than others.
        lines += ["## Rows carried over from an earlier invocation", "",
                  "These were not re-measured by the run that wrote this file, "
                  "and - this matters more - they were scored against the LABELS "
                  "AS THEY STOOD THEN. If a label has been corrected since, these "
                  "rows and the re-measured ones are not comparable. The code, the "
                  "catalogue and the prices may also have moved.",
                  "", "| cell | measured |", "|---|---|"]
        for (version, model), cells in sorted(carried.items()):
            when = sorted({c.get("measured_at") or "not recorded" for c in cells})
            lines.append(f"| {version} {model} | {', '.join(when)} |")
        lines.append("")

    with open(f"{out}.json", "w", encoding="utf-8") as handle:
        json.dump({f"{v}|{m}": cells for (v, m), cells in table.items()},
                  handle, ensure_ascii=False, indent=2)
    with open(f"{out}.md", "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    # THE LABELS GET AUDITED TOO, AUTOMATICALLY AND FOR FREE.
    # A benchmark measures models against labels and silently assumes the labels
    # are right. Ours were not: on dev, 4 of 50 turned out to be wrong, which is
    # 8 points of "model error" that was ours. Every model that just ran read the
    # same tickets, so the disagreement analysis costs no API calls at all - it
    # reads the run files written above. It only ever FLAGS: changing a label
    # because models disagreed would turn the test set into a mirror of the
    # models, and the accuracy column would start measuring nothing.
    if not args.limit:
        print()
        for field in ("category", "priority", "next_step"):
            _, buckets, audit_path = analyse(
                args.set, field, [v for v in versions if v != "v1"])
            if not audit_path:
                continue
            unanimous = len(buckets.get("UNANIMOUS", []))
            majority = len(buckets.get("MAJORITY", []))
            print(f"label audit / {field:10} {unanimous} unanimous + {majority} "
                  f"majority disagreements -> "
                  f"{os.path.relpath(audit_path, ROOT)}")
        print("Read those before trusting the accuracy column: a ticket every "
              "model reads the same way, and we read differently, is a question "
              "about the label.")

    total = sum(c["cost_usd"] for cells in table.values() for c in cells)
    empty = [f"{v} {m}" for (v, m), cells in table.items() if not cells]
    if empty:
        progress.line("CELLS THAT PRODUCED NOTHING: " + ", ".join(empty))
    print()
    if args.rescore:
        # The money was spent by the runs being rescored, not by this invocation.
        print(f"no API calls; ${total:.4f} is what these runs cost when they were "
              f"measured  ->  {os.path.relpath(out + '.md', ROOT)}")
    else:
        print(f"total ${total:.4f}  ->  {os.path.relpath(out + '.md', ROOT)}")


if __name__ == "__main__":
    main()
