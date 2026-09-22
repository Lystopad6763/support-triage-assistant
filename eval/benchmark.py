"""Run ONE frozen prompt across many models, and put the numbers side by side.

    python eval/benchmark.py --dry-run              # план і кошторис, без запитів
    python eval/benchmark.py                        # раунд 1: 50 випадкових рядків
    python eval/benchmark.py --sample 0             # те саме на всіх 157
    python eval/benchmark.py --models a,b,c --repeats 3   # раунд 2: смуга для шортліста

WHY A SEPARATE FILE AND NOT A SHELL LOOP
    The composition of the benchmark is a decision, and decisions belong in the
    repo rather than in someone's shell history: which models, why each one is
    there, and the rule for picking the winner - all below, all readable before
    the first request is sent. A loop over `--model` would produce the same rows
    and leave none of that behind.

    Scoring is imported from eval/run.py, not reimplemented. Same macro-F1, same
    core floor, same violation counter, same ledger. A second copy of the metric
    is a second chance for the model table and the prompt table to disagree.

WHAT IS HELD IDENTICAL, AND WHY THAT IS THE ONLY FAIR COMPARISON
    Every model gets the SAME prompt (frozen v4), the SAME set, and the same
    settings: temperature 0 where the endpoints support it, json_schema, no
    reasoning effort, no output cap. That intersection is the most any vendor
    supports in common. Giving one model a tuned parameter would turn the table
    into a comparison of tuning effort. Per-model adaptation is round two, and
    app/config.py holds those overrides so it stays reproducible.

    Models are run SEQUENTIALLY, rows in parallel inside each model. Running
    models concurrently would make every latency number a measurement of our own
    saturated connection instead of the provider's.

WHAT THE TABLE CANNOT TELL YOU
    Latency comes from OpenRouter's routing at this hour, not from the vendor's
    SLA. And with 157 rows a gap under ~10pp between two models is not a gap -
    see RESOLUTION_NOTE in run.py. That is what --repeats is for.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import random
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import PROMPTS, Settings                          # noqa: E402
from eval.run import (LEDGER, REPORTABLE_N, append_ledger, load_set,  # noqa: E402
                      read_run, report, run_set, score, spread_report,
                      write_table)

PARAMS = ROOT / "data" / "model_params.json"


# --- the composition, with the reason each row is here ------------------------
# Every entry says what question it answers. A candidate that answers no question
# is a candidate that costs money for a row in a table nobody reads.
CANDIDATES: tuple[tuple[str, str], ...] = (
    ("openai/gpt-4o-mini-2024-07-18",
     "база: весь промпт відточено саме на ній, тому вона й точка відліку. "
     "Приймає temperature, seed і structured_outputs, один ендпоінт - отже "
     "без розкиду від маршрутизації"),
    ("openai/gpt-4.1-nano",
     "дешевша за базу ($0,10 проти $0,15 за М вх) і з тим самим набором "
     "параметрів: пряма перевірка, чи ми не переплачуємо"),
    ("openai/gpt-4.1-mini",
     "середній щабель того самого вендора: скільки якості купує 2,7x ціни"),
    ("openai/gpt-5-nano",
     "найдешевша з усіх, $0,025 за М вх - у шість разів дешевше за базу. "
     "temperature не приймає жоден її ендпоінт, це піде в колонку 'скинуто'"),
    ("openai/gpt-5-mini",
     "уміє reasoning, але в раунді 1 його не отримує: питання саме в тому, "
     "чи кращий базовий режим нової моделі за старшу без нього"),
    ("google/gemini-2.5-flash-lite",
     "найдешевша серед тих, що тримають повний набір параметрів ($0,05): "
     "інший вендор, ті самі умови"),
    ("google/gemini-3.1-flash-lite",
     "новіша Google того ж класу, втричі дорожча за 2.5 на виході - чи є за що"),
    ("anthropic/claude-haiku-4.5",
     "дешевий щабель Anthropic; structured_outputs є лише на частині "
     "ендпоінтів, тому це ще й перевірка нашої маршрутизації"),
    ("anthropic/claude-sonnet-5",
     "стеля за грошима, ~$63 на 10k проти $3. Єдина річ, яку вона тут "
     "вирішує, головна: журнал Р-126 каже, що 32 хибні факти на еталонних P3 - "
     "це межа МОДЕЛІ, а не промпту. Якщо сильна модель дає ті самі 32, "
     "твердження підтверджено; якщо менше - межа була наша"),
    ("qwen/qwen3-max",
     "не-західний вендор із повним набором параметрів; чверть корпусу не "
     "англійською, і це єдиний спосіб дізнатись, чи це для неї перевага"),
)

# --- the rule for picking a winner, written before the first request ----------
# v6 and v7 cost $0.14 to prove that a rule invented after seeing the numbers is
# not a rule. So this one is here, in the file, and it prints at every run.
DECISION_RULE = """\
правило вибору, оголошене до прогону:
  1. дискваліфікація: збоїв більше 5% рядків, і вони не rate_limit. Модель, яка
     не вміє віддати контракт, не кандидат - хоч би що показували її метрики.
  2. шортліст: три найвищі за головним числом (macro-F1 core по трьох полях).
  3. раунд 2: --repeats 3 на шортлісті, кожна модель отримує ВЛАСНУ смугу, бо
     дисперсія - властивість моделі, а не промпту (журнал Р-120).
  4. переможець: найвище середнє, якщо відрив від наступної більший за більшу з
     двох смуг. Якщо відрив усередині смуги - виграє дешевша за $/10k. Якщо й
     тут рівно - нижча p95.
  5. дивимось не лише головне число: v6 показав, що воно ховає обвал окремого
     класу (F1 по P1 -0,150 при -0,037 на головному). Тому в таблиці є всі три
     поля, і різниця в пріоритеті важить більше за різницю в кроці."""

# The sweep's default row count, chosen for speed. What it costs is written at
# the --sample flag and printed by sample_shape() before every run.
DEFAULT_SAMPLE = 50

# Measured on v4 / dev / gpt-4o-mini, 157 rows: 2 718 input and 88 output tokens
# per row. Used only for the --dry-run estimate; the real cost is metered per run
# from the provider's own usage numbers.
TOKENS_IN_PER_ROW = 2718
TOKENS_OUT_PER_ROW = 88


def prices() -> dict[str, tuple[float, float]]:
    """Input/output price per million, from the last probe. Missing model -> 0,
    and the estimate says so rather than inventing a number."""
    if not PARAMS.exists():
        return {}
    d = json.loads(PARAMS.read_text(encoding="utf-8"))
    out = {}
    for name, v in d.get("models", {}).items():
        try:
            out[name] = (min(v["price_in_per_m"]), min(v["price_out_per_m"]))
        except (KeyError, ValueError):
            continue
    return out


def probe_age() -> str:
    if not PARAMS.exists():
        return "проби немає - запустіть scripts/probe_models.py"
    d = json.loads(PARAMS.read_text(encoding="utf-8"))
    when = d.get("probed_at", "?")
    return "проба параметрів і цін: %s" % when


def dropped_for(model: str) -> str:
    """Which of our settings this model's endpoints do not accept, from the probe.
    Printed before the run so nobody reads the table thinking every row was
    measured at temperature 0 - that exact illusion cost us the first pass."""
    if not PARAMS.exists():
        return "?"
    d = json.loads(PARAMS.read_text(encoding="utf-8"))
    v = d.get("models", {}).get(model)
    if not v:
        return "невідомо"
    inter = set(v.get("all", []))
    missing = [p for p in ("temperature", "seed", "structured_outputs")
               if p not in inter]
    return ",".join(missing) if missing else "—"


def subsample(rows: list[dict], n: int, seed: int) -> list[dict]:
    """A fixed random subset, identical for every model in the sweep.

    Seeded and then sorted by id, so the same --sample gives the same rows on
    every machine and every rerun: a benchmark where each model saw a different
    50 tickets would be measuring the draw, not the models. The sample is taken
    ONCE in main(), before the model loop, so fairness is structural rather than
    a promise.
    """
    if n >= len(rows):
        return rows
    picked = random.Random(seed).sample(rows, n)
    return sorted(picked, key=lambda r: r["id"])


def sample_shape(rows: list[dict]) -> None:
    """Print what the subset does to the class counts, because that is the part
    a smaller set silently takes away.

    The headline averages only classes with support >= REPORTABLE_N. Shrink the
    set and classes drop out of it one by one - so the same metric name starts
    meaning a different average, and the number stops being comparable with the
    157-row prompt table. Printed, not hidden, and printed BEFORE the money is
    spent.
    """
    import collections
    fields = (("категорія", "category"), ("пріоритет", "priority"),
              ("наступний крок", "next_step"))
    print()
    print("склад вибірки (поріг для головного числа: n >= %d)" % REPORTABLE_N)
    for ua, en in fields:
        counts = collections.Counter(r["розмітка"][ua] for r in rows)
        keep = [k for k, v in counts.items() if v >= REPORTABLE_N]
        line = ", ".join("%s %d%s" % (k, v, "" if v >= REPORTABLE_N else " ↓")
                         for k, v in counts.most_common())
        print("  %-14s %s" % (en, line))
        print("  %-14s у головне число входить %d клас(и) з %d"
              % ("", len(keep), len(counts)))


def plan(models: list[str], rows: int, repeats: int) -> None:
    pr = prices()
    print(probe_age())
    print("\n%-40s %8s %8s %9s  %s"
          % ("модель", "$ прогін", "$ на 10k", "скинуто", ""))
    total = 0.0
    for m in models:
        pin, pout = pr.get(m, (0.0, 0.0))
        per_row = (TOKENS_IN_PER_ROW * pin + TOKENS_OUT_PER_ROW * pout) / 1e6
        run_cost = per_row * rows * repeats
        total += run_cost
        note = "" if m in pr else "  (ціни немає в пробі)"
        print("%-40s %8.3f %8.2f %9s%s"
              % (m, run_cost, per_row * 10000, dropped_for(m), note))
    print("%-40s %8.3f" % ("РАЗОМ", total))
    print("\nоцінка за виміряними токенами v4: %d вх + %d вих на рядок; "
          "справжня ціна лічиться з відповідей провайдера"
          % (TOKENS_IN_PER_ROW, TOKENS_OUT_PER_ROW))
    # The estimate is a no-cache upper bound and it should be read as one. The
    # measured v4 run came in at $2.99 per 10k against $4.61 here, because 339k
    # of its 427k input tokens were served from the prompt cache: the system
    # prompt is identical for all 157 rows. Whether other vendors cache at all,
    # and on what key, is one of the questions this table answers.
    print("це оцінка БЕЗ кешу промпту - верхня межа. Виміряний v4 дав $2,99 "
          "проти $4,61 тут саме за рахунок кешу")


# --- the comparison table ----------------------------------------------------
TABLE_COLS = [
    ("модель", lambda r: r["model"]),
    ("збоїв", lambda r: r["s"]["failures"]),
    ("скинуто", lambda r: r["dropped"] or "—"),
    ("головне", lambda r: r["s"]["headline"]),
    # The core average drops classes below REPORTABLE_N, and on a small
    # sample that can leave one class per field. This one keeps every
    # class: noisier per class, but it does not quietly become the
    # majority class's F1.
    ("головне (усі)", lambda r: sum(
        r["s"]["fields"][f]["macro_f1_all"]
        for f in ("category", "priority", "next_step")) / 3),
    ("F1 катег", lambda r: r["s"]["fields"]["category"]["macro_f1_core"]),
    ("F1 пріор", lambda r: r["s"]["fields"]["priority"]["macro_f1_core"]),
    ("F1 крок", lambda r: r["s"]["fields"]["next_step"]["macro_f1_core"]),
    ("acc пріор", lambda r: r["s"]["fields"]["priority"]["accuracy"]),
    ("усі три", lambda r: r["s"]["all_three_exact"]),
    # These three are dicts in the summary - {"n": .., "cases": [..]} - because
    # the per-row detail is what makes them fixable. The table wants the count;
    # the cases stay in the run's own .summary.json and .table.md.
    ("порушень", lambda r: r["s"]["table_violations"]["n"]),
    ("суперечн", lambda r: r["s"]["self_contradiction"]["n"]),
    ("цитата вигадана", lambda r: r["s"]["evidence_invented"]["n"]),
    ("ескал знайдено", lambda r: "%d/%d" % (r["s"]["escalation"]["found"],
                                            r["s"]["escalation"]["gold"])),
    ("$ за тікет", lambda r: r["s"]["cost"]["per_ticket_usd"]),
    ("$ за 10k", lambda r: r["s"]["cost"]["per_10k_usd"]),
    ("з кешу вх", lambda r: r["s"]["cost"]["cached_input_tokens"]),
    # Non-zero only for the reasoning models. Billed as output, absent from
    # the answer: without this column their cost has no visible cause.
    ("думання", lambda r: r["s"]["cost"].get("reasoning_tokens")),
    ("токени вх", lambda r: r["s"]["cost"]["input_tokens"]),
    ("p50 мс", lambda r: r["s"]["latency_ms"]["p50"]),
    ("p95 мс", lambda r: r["s"]["latency_ms"]["p95"]),
]


def cell(v) -> str:
    if v is None:
        return "н/д"
    if isinstance(v, float):
        return ("%.3f" % v).replace(".", ",")
    return str(v)


def safe(fn, row):
    """A model that never returned an answer still needs a row in the table.

    Its summary is None and every extractor above would raise on it - which is
    exactly what happened the first time this was tested: one failed model took
    down the table at the END of a paid sweep, after every request was already
    spent. So each cell is allowed to be missing, and missing prints as "н/д".
    """
    try:
        return fn(row)
    except (TypeError, KeyError, IndexError, AttributeError):
        return None


def write_comparison(results: list[dict], path: Path, meta: dict) -> None:
    """One CSV and one markdown table, both sorted by the headline.

    Same dialect as the metric ledger - ';' and a BOM - because these files are
    opened in Excel by whoever reads the report, and a comma-delimited UTF-8 file
    without a BOM lands there as one column of mojibake.
    """
    def key(r):
        h = safe(lambda x: x["s"]["headline"], r)
        return (h is None, -(h or 0))

    ordered = sorted(results, key=key)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL,
                   lineterminator="\n")
    w.writerow([c[0] for c in TABLE_COLS] + ["помилка"])
    for r in ordered:
        w.writerow([cell(safe(f, r)) for _, f in TABLE_COLS]
                   + [r.get("error", "")])
    path.write_text(buf.getvalue(), encoding="utf-8-sig")

    md = ["# Бенчмарк моделей — промпт %s, набір %s, %d рядків"
          % (meta["prompt"], meta["set"], meta["rows"]), "",
          "Промпт заморожений: усі моделі бачать той самий текст і ті самі "
          "налаштування. Колонка «скинуто» — параметри, яких ендпоінти моделі "
          "не приймають; це не наш вибір, а межа вендора.", "",
          "Латентність зміряна на **%d паралельних запитах**, однаково для всіх "
          "моделей. Це не SLA вендора і не час одного запиту: при іншій "
          "конкурентності числа будуть інші, тому порівнювати їх можна лише "
          "всередині цієї таблиці та з прогонами промптів, зміряними так само."
          % meta.get("workers", 0), "",
          "| " + " | ".join(c[0] for c in TABLE_COLS) + " |",
          "|" + "|".join("---" for _ in TABLE_COLS) + "|"]
    for r in ordered:
        md.append("| " + " | ".join(cell(safe(f, r))
                                    for _, f in TABLE_COLS) + " |")
    md += ["", "## Чому кожна модель у таблиці", ""]
    for name, why in CANDIDATES:
        if any(r["model"] == name for r in results):
            md.append("- **%s** — %s" % (name, why))
    md += ["", "## Правило вибору", "", "```", DECISION_RULE, "```"]
    failed = [r for r in results if r.get("error")]
    if failed:
        md += ["", "## Не дійшли до метрик", ""]
        md += ["- **%s** — %s" % (r["model"], r["error"]) for r in failed]
    path.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--prompt", default="v4",
                    help="заморожена версія; типово v4")
    ap.add_argument("--set", default="dev",
                    choices=["dev", "golden", "synthetic", "eval", "fewshot"],
                    help="dev - набір для відбору. golden тримаємо чистим для "
                         "одного фінального заміру переможця")
    ap.add_argument("--models", default=None,
                    help="через кому; типово всі кандидати з CANDIDATES")
    ap.add_argument("--limit", type=int, default=0,
                    help="перші N рядків - для смоуку, не для заміру")
    # 50 by default: a third of the wall clock, at a stated price. Only ONE
    # class per field clears REPORTABLE_N at this size, so `головне` degenerates
    # into the majority class's F1 and is NOT comparable with the 157-row prompt
    # table. That is why the table carries `головне (усі)` beside it - every
    # class, regardless of support - and why sample_shape() prints the damage
    # before the first request. --sample 0 measures all 157; 120 is the smallest
    # sample whose core set still matches the prompt table.
    ap.add_argument("--sample", type=int, default=None,
                    help="випадкові N рядків, однакові для всіх моделей; "
                         "типово 50. --sample 0 - увесь набір")
    ap.add_argument("--sample-seed", type=int, default=20260922,
                    help="зерно вибірки; те саме зерно - та сама вибірка")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--repeats", type=int, default=1,
                    help="раунд 2: власна смуга для кожної моделі")
    ap.add_argument("--dry-run", action="store_true",
                    help="план, кошторис і правило вибору. Без запитів")
    args = ap.parse_args()

    models = ([m.strip() for m in args.models.split(",") if m.strip()]
              if args.models else [m for m, _ in CANDIDATES])
    prompt = PROMPTS[args.prompt]
    rows = load_set(args.set)
    if args.sample is not None and args.limit:
        raise SystemExit("--sample і --limit разом не мають сенсу: "
                         "оберіть випадкову вибірку або перші N")
    # --limit is the smoke path, so it turns the default sample off rather than
    # colliding with it; an explicit --sample always wins over both.
    args.sample = args.sample if args.sample is not None else (
        0 if args.limit else DEFAULT_SAMPLE)
    if args.sample:
        rows = subsample(rows, args.sample, args.sample_seed)
    elif args.limit:
        rows = rows[:args.limit]

    print("бенчмарк: промпт %s (заморожений), набір %s, %d рядків, "
          "%d моделей, повторів %d"
          % (prompt.version, args.set, len(rows), len(models), args.repeats))
    print()
    print(DECISION_RULE)
    print()
    plan(models, len(rows), args.repeats)
    if args.sample:
        sample_shape(rows)
    if args.dry_run:
        print("\nсухий прогін: жодного запиту не надіслано, витрат нуль.")
        return
    if args.set in ("golden", "eval"):
        print("\nУВАГА: golden призначений для ОДНОГО фінального заміру "
              "переможця. Відбір моделі на ньому робить його другим dev.")

    settings = Settings()
    settings.runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    results: list[dict] = []

    for i, model in enumerate(models, 1):
        print("\n" + "=" * 78)
        print("[%d/%d] %s   скинуто: %s" % (i, len(models), model,
                                            dropped_for(model)))
        print("=" * 78)
        summaries, paths = [], []
        try:
            for attempt in range(args.repeats):
                if args.repeats > 1:
                    print("-- повтор %d з %d" % (attempt + 1, args.repeats))
                run_stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
                slug = model.replace("/", "-")
                out = (settings.runs_dir
                       / f"{run_stamp}_{prompt.version}_{slug}_{args.set}.jsonl")
                records = run_set(rows, prompt, settings, model, args.workers,
                                  None, out, show=0, set_name=args.set)
                s = score(records)
                header, _ = read_run(out)
                out.with_suffix(".summary.json").write_text(
                    json.dumps(s, ensure_ascii=False, indent=2),
                    encoding="utf-8")
                write_table(records, out.with_suffix(".table.md"), header)
                append_ledger(s, header, out.name)
                summaries.append(s)
                paths.append(out)
        except Exception:                       # one bad model, not a dead sweep
            print("!! %s не дійшла до метрик:" % model)
            traceback.print_exc(limit=3)
            results.append({"model": model, "s": None,
                            "dropped": dropped_for(model),
                            "error": "виняток під час прогону, див. консоль"})
            continue

        row = {"model": model, "s": summaries[-1], "dropped": dropped_for(model),
               "runs": [p.name for p in paths]}
        if args.repeats > 1:
            row["spread"] = spread_report(summaries)
            print("розмах головного: %.4f"
                  % (row["spread"]["headline"]["range"] or 0))
        results.append(row)
        report(summaries[-1], read_run(paths[-1])[0])

    scored = [r for r in results if r.get("s")]
    if not scored:
        raise SystemExit("жодна модель не дійшла до метрик")

    out_csv = settings.runs_dir / f"benchmark_{stamp}_{prompt.version}_{args.set}.csv"
    meta = {"prompt": prompt.version, "set": args.set, "rows": len(rows),
            "repeats": args.repeats, "stamp": stamp, "workers": args.workers,
            "sample": args.sample or None, "sample_seed": args.sample_seed,
            "sampled_ids": [r["id"] for r in rows] if args.sample else None}
    write_comparison(scored + [r for r in results if not r.get("s")],
                     out_csv, meta)
    (out_csv.with_suffix(".json")).write_text(json.dumps(
        {"meta": meta, "decision_rule": DECISION_RULE,
         "candidates": {m: why for m, why in CANDIDATES},
         "results": [{k: v for k, v in r.items() if k != "s"} | {
             "headline": (r["s"] or {}).get("headline"),
             "fields": {f: (r["s"] or {}).get("fields", {}).get(f, {})
                        .get("macro_f1_core") for f in
                        ("category", "priority", "next_step")},
             "failures": (r["s"] or {}).get("failures"),
             "per_10k": ((r["s"] or {}).get("cost") or {}).get("per_10k"),
         } for r in results]},
        ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("ЗВЕДЕННЯ  (сортовано за головним числом)")
    print("=" * 78)
    head = ["модель", "збої", "головне", "F1 пр", "усі 3", "$/10k", "p50"]
    widths = [40, 5, 8, 7, 7, 7, 6]
    print(" ".join(h.ljust(w) for h, w in zip(head, widths)))
    for r in sorted(scored, key=lambda r: -(r["s"]["headline"] or 0)):
        s = r["s"]
        vals = [r["model"], s["failures"], cell(s["headline"]),
                cell(s["fields"]["priority"]["macro_f1_core"]),
                cell(s["all_three_exact"]), cell(s["cost"]["per_10k_usd"]),
                s["latency_ms"]["p50"]]
        print(" ".join(str(v).ljust(w) for v, w in zip(vals, widths)))
    for r in results:
        if r.get("error"):
            print("%-40s %s" % (r["model"], r["error"]))
    print("\nтаблиця: %s\n         %s\n         %s\nжурнал метрик: %s"
          % (out_csv, out_csv.with_suffix(".md"), out_csv.with_suffix(".json"),
             LEDGER))


if __name__ == "__main__":
    main()
