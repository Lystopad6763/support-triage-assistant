"""Run a prompt version over a frozen set, and score what came back.

    python eval/run.py --set dev                    # iterate here
    python eval/run.py --set eval                   # golden + synthetic, 250
    python eval/run.py --set eval --repeats 3       # + the spread, before promoting
    python eval/run.py --score data/runs/<file>.jsonl    # no API calls

ONE FILE, TWO ENTRY POINTS, AND WHY
    Running and scoring are one command because the only hard requirement is
    that scoring must not cost money twice: every raw answer is written to
    data/runs/ before anything is measured, and --score reads that file. Two
    modules would add a contract between them to keep in sync for no gain at
    this size. The scoring functions stay importable, so the model benchmark
    scores its runs with exactly this code rather than a second copy.

WHAT IS MEASURED, AND WHY NOT ACCURACY
    The labels are brutally skewed - `refund_and_cancel` is 73.4% of next_step,
    P3 is 58.3% of priority. A model that answers the modal value for every
    field scores about 73% / 42% / 58% on plain accuracy while understanding
    nothing. So the headline number is MACRO F1: every class weighs the same,
    and a rare class answered never costs as much as a common class answered
    wrong. Plain accuracy is printed beside it, to show the gap.

    Macro is taken twice. `core` averages only the classes with support of at
    least REPORTABLE_N and is what decisions use; `all` averages everything and
    is printed next to it so the narrowing is visible. Classes under the floor
    appear as counts - "2 of 5" - because a percentage over five rows is not a
    percentage. And no version is called better on a single run: --repeats
    reports the range, and a gain smaller than the range is the same version
    twice.

    Five things are counted that are not accuracy at all:
      - table violations: a next_step the category does not allow. The schema
        cannot express this, so it is the one rule the model can break while
        returning perfectly valid JSON.
      - failures: no object at all - invalid JSON, refusal, timeout, 429.
      - cost per ticket, and the projection to 10,000 tickets a month, which is
        the number the assignment asks for.
      - latency p50/p95/p99, because a triage that takes 8s per ticket is not
        deployable however accurate.
      - escalation on its own: found N of M, with the missed ids named. Its
        error is asymmetric and in a macro average over seven classes it
        disappears.

    And two breakdowns, because a single average hides both: by language (a
    quarter of the corpus is not English) and by set (golden is real tickets,
    synthetic is the hand-written edge cases, and they fail differently).
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import datetime as dt
import io
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import taxonomy                                          # noqa: E402
from app.cache import Cache                                       # noqa: E402
from app.config import PROMPTS, Settings                          # noqa: E402
from app.llm import classify, render                              # noqa: E402

SETS = ROOT / "data" / "sets"
FIELDS = (("категорія", "category"), ("пріоритет", "priority"),
          ("наступний крок", "next_step"))

# Below this support a per-class percentage is not a number, it is a mood.
# Clopper-Pearson, one-sided 95% lower bound on a PERFECT cell: n=10 buys 74.1%,
# n=15 buys 81.9%, n=20 buys 86.1%. So "3 of 3 correct" does not even establish
# that the class is better than 60%. Classes under the floor are reported as
# counts - "2 of 5" - and kept out of the headline average; they still act as a
# regression guard, because a count that falls is a fact even when a rate is not.
REPORTABLE_N = 15

# The paired-comparison limit, for the model table later: at 20% discordance
# McNemar needs 57 rows to resolve a 15pp gap, 145 for 10pp and 616 for 5pp. On
# 250 rows a 3pp difference between two models is not a difference.
RESOLUTION_NOTE = ("на 250 рядках роздільні різниці від ~10 в.п.; "
                   "менше — не різниця")

FAILURE_KINDS = (
    ("timeout", lambda e: e.startswith("timeout:")),
    ("rate_limit", lambda e: "HTTP 429" in e),
    ("provider_5xx", lambda e: any("HTTP 5%d" % d in e for d in range(10))),
    ("invalid_json", lambda e: "invalid JSON" in e),
    ("transport", lambda e: e.startswith("transport:")),
    ("http_4xx", lambda e: "HTTP 4" in e),
)


# --- loading -----------------------------------------------------------------

def load_set(name: str) -> list[dict]:
    """`eval` is golden + synthetic: the 250 rows every version is scored on."""
    names = ["golden", "synthetic"] if name == "eval" else [name]
    rows = []
    for n in names:
        path = SETS / f"{n}_v1.json"
        if not path.exists():
            raise SystemExit(f"немає набору {path}")
        for r in json.loads(path.read_text(encoding="utf-8")):
            r["набір"] = n
            rows.append(r)
    return rows


def ticket_text(row: dict) -> str:
    title = row["заголовок"].strip()
    body = row["оригінал"]
    return f"{title}\n\n{body}".strip() if title else body


# --- running -----------------------------------------------------------------

def show_request(prompt, model: str, settings: Settings) -> None:
    """Print the system message and the parameters, exactly as they will be sent.

    Printed once, not per ticket: the system message is identical for all 250 and
    repeating 7,500 characters would bury the answers. The parameter line matters
    as much as the text - `dropped` names what this model's endpoints refuse, so
    a run cannot silently claim a temperature the provider never received.
    """
    from app.llm import dropped_params
    text = render(prompt)
    print("=" * 78)
    print("SYSTEM (%d знаків, %s)" % (len(text), prompt.version))
    print("=" * 78)
    print(text)
    print("=" * 78)
    print("модель %s | temperature %s | seed %s | формат %s | effort %s"
          % (model, prompt.temperature, prompt.seed, prompt.response_format,
             prompt.reasoning_effort))
    dropped = dropped_params(model, prompt)
    print("параметри, які ця модель НЕ приймає і які будуть скинуті: %s"
          % (", ".join(dropped) if dropped else "немає"))
    print("=" * 78)


def show_exchange(row: dict, text: str, res) -> None:
    """One ticket: what went out as the user turn, and what came back."""
    print("\n" + "-" * 78)
    print("USER  %s  (%s, %s, %d знаків)"
          % (row["id"], row["набір"], row["мова"] or "-", len(text)))
    print("-" * 78)
    print(text)
    print("-" * 78)
    t = res.triage
    if t is None:
        print("ВІДПОВІДІ НЕМА: %s" % res.error)
        if res.raw:
            print("сире тіло: %s" % res.raw[:600])
        return
    gold = row["розмітка"]
    if t.priority_facts:
        print("facts:     %s" % ", ".join(f.value for f in t.priority_facts))
    elif getattr(res, "asks_facts", None) is not False:
        print("facts:     [] (порожньо — за правилом це P3)")
    print("ASSISTANT  %s / %s / %s"
          % (t.category.value, t.priority.value, t.next_step.value))
    print("еталон     %s / %s / %s"
          % (gold["категорія"], gold["пріоритет"], gold["наступний крок"]))
    print("evidence:  %s" % (t.evidence or "(порожньо)"))
    print("rationale: %s" % t.rationale)
    if t.secondary_categories:
        print("secondary: %s" % ", ".join(c.value for c in t.secondary_categories))
    print("токени %d/%d, $%.6f, %d мс, %d спроб%s"
          % (res.input_tokens, res.output_tokens, res.cost_usd, res.latency_ms,
             res.attempts, ", полагоджено" if res.repaired else ""))


def run_set(rows: list[dict], prompt, settings: Settings, model: str | None,
            workers: int, cache: Cache | None, out_path: Path,
            show: int = 0, set_name: str = "") -> list[dict]:
    """Classify every row, writing each answer as it lands.

    Written per answer rather than at the end so a run killed halfway is still
    a run: 250 tickets is minutes of wall clock and real money, and losing it
    to a KeyboardInterrupt would be paying twice for the same measurement.
    """
    records: list[dict] = []
    done = 0
    asks_facts = getattr(prompt, "contract", "triage") == "triage_facts"
    with io.open(out_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "kind": "header",
            "prompt_version": prompt.version,
            "model": model or prompt.model,
            "temperature": prompt.temperature,
            "seed": prompt.seed,
            "response_format": prompt.response_format,
            "reasoning_effort": prompt.reasoning_effort,
            "tested_on": prompt.tested_on,
            "set": set_name,
            "rows": len(rows),
            # Latency is meaningless without it. p50 measured at 12 parallel
            # requests is not p50 measured at 6, and until now neither the run
            # file nor the ledger recorded which one produced the number - so
            # two runs at different concurrency would have sat in the same
            # column looking comparable.
            "workers": workers,
            "started_at": dt.datetime.now().isoformat(timespec="seconds"),
            "prompt_chars": len(render(prompt)),
        }, ensure_ascii=False) + "\n")
        fh.flush()

        def one(row):
            text = ticket_text(row)
            res = classify({"ticket_id": row["id"], "text": text},
                           settings, model=model, prompt=prompt, cache=cache)
            return row, res, text

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for row, res, text in pool.map(one, rows):
                t = res.triage
                # The prompt demands a span copied verbatim. Checked here, where
                # the ticket text is in hand: a model that invents the quote is
                # grounding its answer in words the ticket does not contain, and
                # that is invisible in any accuracy number.
                verbatim = (None if not (t and t.evidence)
                            else " ".join(t.evidence.split())
                            in " ".join(text.split()))
                rec = {
                    "id": row["id"],
                    "набір": row["набір"],
                    "мова": row["мова"],
                    "gold": {new: row["розмітка"][old] for old, new in FIELDS},
                    "pred": ({"category": t.category.value,
                              "priority": t.priority.value,
                              "next_step": t.next_step.value} if t else None),
                    "secondary": ([c.value for c in t.secondary_categories]
                                  if t else []),
                    # null, not [], when the contract never asked: an empty list
                    # we defaulted is not the model saying "no facts", and
                    # counting it as one would invent a contradiction on every
                    # v1 and v2 row.
                    "priority_facts": ([f.value for f in t.priority_facts]
                                       if t and asks_facts else None),
                    "evidence": t.evidence if t else "",
                    "evidence_verbatim": verbatim,
                    "rationale": t.rationale if t else "",
                    "confidence": t.confidence if t else None,
                    "ok": res.ok,
                    "error": res.error,
                    "attempts": res.attempts,
                    "repaired": res.repaired,
                    "latency_ms": res.latency_ms,
                    "input_tokens": res.input_tokens,
                    "output_tokens": res.output_tokens,
                    "cached_input_tokens": res.cached_input_tokens,
                    # Billed as output and invisible in the answer. Collected by
                    # app/llm.py since the first pass but never written here, so
                    # it reached no summary and no table - which is exactly the
                    # column that explains a reasoning model's cost in the model
                    # benchmark, where gpt-5-mini and gpt-5-nano both appear.
                    "reasoning_tokens": res.reasoning_tokens,
                    "cost_usd": res.cost_usd,
                    "cache_hit": res.cache_hit,
                    "provider": res.provider,
                    "system_fingerprint": res.system_fingerprint,
                    "logprob_mean": res.logprob_mean,
                    "params_dropped": res.params_dropped,
                }
                records.append(rec)
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                done += 1
                if show < 0 or done <= show:
                    show_exchange(row, text, res)
                    continue
                mark = "." if res.ok else "x"
                sys.stdout.write(mark)
                if done % 50 == 0:
                    sys.stdout.write(" %d\n" % done)
                sys.stdout.flush()
    sys.stdout.write("\n")
    return records


# --- scoring -----------------------------------------------------------------

def per_class(pairs: list[tuple[str, str]]) -> dict:
    """Precision, recall, F1 and support for every label that appears at all.

    A class predicted never gets F1 0 and still counts in the macro average -
    that is the whole point of macro on a set where one class is 73%.
    """
    labels = sorted({g for g, _ in pairs} | {p for _, p in pairs if p})
    out = {}
    for lab in labels:
        tp = sum(1 for g, p in pairs if g == lab and p == lab)
        fp = sum(1 for g, p in pairs if g != lab and p == lab)
        fn = sum(1 for g, p in pairs if g == lab and p != lab)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out[lab] = {"precision": prec, "recall": rec, "f1": f1,
                    "support": sum(1 for g, _ in pairs if g == lab),
                    "predicted": sum(1 for _, p in pairs if p == lab)}
    return out


def confusions(pairs: list[tuple[str, str]], top: int = 5) -> list:
    c = collections.Counter((g, p) for g, p in pairs if p and g != p)
    return [{"gold": g, "pred": p, "n": n} for (g, p), n in c.most_common(top)]


def score(records: list[dict]) -> dict:
    ok = [r for r in records if r["ok"] and r["pred"]]
    failed = [r for r in records if not (r["ok"] and r["pred"])]
    summary: dict = {
        "rows": len(records),
        "scored": len(ok),
        "failures": len(failed),
        "failure_ids": [r["id"] for r in failed][:20],
        "repaired": sum(1 for r in records if r["repaired"]),
        "fields": {},
    }

    for field in ("category", "priority", "next_step"):
        pairs = [(r["gold"][field], r["pred"][field]) for r in ok]
        classes = per_class(pairs)
        big = {k: v for k, v in classes.items() if v["support"] >= REPORTABLE_N}
        # Two averages, both printed. `core` decides - it covers only classes
        # whose support can carry a percentage. `all` is shown beside it so the
        # narrowing is visible rather than a quiet convenience: on next_step it
        # averages 3 classes instead of 7, and four of those seven have n=3-7,
        # where one flipped ticket moves a class F1 by 0.2 and the average by
        # 0.03. A version promoted on that is promoted on noise.
        # None, not 0.0: on a small smoke run no class reaches the floor, and a
        # printed 0.000 reads as "scored zero" instead of "not scorable here".
        macro_core = (statistics.fmean(v["f1"] for v in big.values())
                      if big else None)
        macro_all = (statistics.fmean(v["f1"] for v in classes.values())
                     if classes else 0.0)
        acc = (sum(1 for g, p in pairs if g == p) / len(pairs)) if pairs else 0.0
        # What a model would score by always answering the commonest label.
        base_label, base_n = collections.Counter(
            g for g, _ in pairs).most_common(1)[0] if pairs else ("", 0)
        summary["fields"][field] = {
            "macro_f1_core": macro_core,
            "macro_f1_all": macro_all,
            "reportable_classes": sorted(big),
            "rare_classes": {
                k: {"correct": sum(1 for g, p in pairs if g == k and p == k),
                    "support": v["support"], "predicted": v["predicted"]}
                for k, v in classes.items() if v["support"] < REPORTABLE_N},
            "accuracy": acc,
            "majority_baseline": {"label": base_label,
                                  "accuracy": base_n / len(pairs) if pairs else 0},
            "per_class": classes,
            "top_confusions": confusions(pairs),
        }
    cores = [summary["fields"][f]["macro_f1_core"]
             for f in ("category", "priority", "next_step")]
    summary["headline"] = (statistics.fmean(cores)
                           if all(c is not None for c in cores) else None)

    summary["all_three_exact"] = (
        sum(1 for r in ok if r["gold"] == r["pred"]) / len(ok) if ok else 0.0)

    # --- the rule the schema cannot express ---------------------------------
    viol = []
    for r in ok:
        cat, step = r["pred"]["category"], r["pred"]["next_step"]
        if not taxonomy.step_allowed(cat, step):
            viol.append({"id": r["id"], "why": f"{cat} -> {step}"})
        elif (step == "escalate_to_authority_case"
              and r["pred"]["priority"] != "P1"):
            viol.append({"id": r["id"], "why": "escalate not P1"})
    summary["table_violations"] = {"n": len(viol), "cases": viol[:10]}

    # --- the model against its own enumeration ------------------------------
    # Only meaningful under the `triage_facts` contract. It is not accuracy: it
    # counts how often the answer contradicts the working the model itself wrote
    # one field earlier, which is the exact defect v3 exists to close.
    self_contra = []
    for r in ok:
        facts = r.get("priority_facts")
        if facts is None:
            continue
        want = taxonomy.priority_from_facts(facts)
        if want != r["pred"]["priority"]:
            self_contra.append({"id": r["id"], "facts": facts,
                                "implies": want, "said": r["pred"]["priority"]})
    summary["self_contradiction"] = {
        "n": len(self_contra),
        "checked": sum(1 for r in ok if r.get("priority_facts") is not None),
        "cases": self_contra[:10],
    }

    # --- escalation, counted on its own ------------------------------------
    # Its error is asymmetric: missing a case already at the bank means a
    # template about refunds goes out to someone whose money is in dispute,
    # while raising one too many costs a lawyer five minutes. In macro F1 it is
    # one class of seven with n=5 and disappears. Counts, not rates.
    step = "escalate_to_authority_case"
    tp = sum(1 for r in ok if r["gold"]["next_step"] == step
             and r["pred"]["next_step"] == step)
    gold_n = sum(1 for r in ok if r["gold"]["next_step"] == step)
    pred_n = sum(1 for r in ok if r["pred"]["next_step"] == step)
    summary["escalation"] = {
        "found": tp, "gold": gold_n, "predicted": pred_n,
        "missed_ids": [r["id"] for r in ok if r["gold"]["next_step"] == step
                       and r["pred"]["next_step"] != step],
        "extra_ids": [r["id"] for r in ok if r["pred"]["next_step"] == step
                      and r["gold"]["next_step"] != step],
    }

    # --- failures, by kind, because the brief names three of them ----------
    kinds = collections.Counter()
    for r in failed:
        err = r.get("error") or ""
        for name, test in FAILURE_KINDS:
            if test(err):
                kinds[name] += 1
                break
        else:
            kinds["other"] += 1
    summary["failures_by_kind"] = dict(kinds)

    # --- evidence actually copied, not paraphrased --------------------------
    invented = [r["id"] for r in ok if r.get("evidence_verbatim") is False]
    summary["evidence_invented"] = {"n": len(invented), "ids": invented[:10],
                                    "checked": sum(
                                        1 for r in ok
                                        if r.get("evidence_verbatim") is not None)}

    # --- breakdowns ---------------------------------------------------------
    for key, name in (("мова", "by_language"), ("набір", "by_set")):
        block = {}
        for value in sorted({r[key] for r in records}):
            sub = [r for r in ok if r[key] == value]
            if not sub:
                block[value or "(порожня)"] = {"n": 0}
                continue
            block[value or "(порожня)"] = {
                "n": len(sub),
                "all_three_exact": sum(1 for r in sub
                                       if r["gold"] == r["pred"]) / len(sub),
                **{f"{f}_acc": sum(1 for r in sub
                                   if r["gold"][f] == r["pred"][f]) / len(sub)
                   for f in ("category", "priority", "next_step")},
            }
        summary[name] = block

    # --- money and time -----------------------------------------------------
    live = [r for r in records if not r["cache_hit"]]
    cost = sum(r["cost_usd"] for r in live)
    lat = sorted(r["latency_ms"] for r in live) or [0]
    summary["cost"] = {
        "total_usd": cost,
        "per_ticket_usd": cost / len(live) if live else 0.0,
        "per_10k_usd": (cost / len(live) * 10_000) if live else 0.0,
        "input_tokens": sum(r["input_tokens"] for r in live),
        "output_tokens": sum(r["output_tokens"] for r in live),
        "cached_input_tokens": sum(r["cached_input_tokens"] for r in live),
        # .get, not [..]: runs recorded before this field existed still score.
        "reasoning_tokens": sum(r.get("reasoning_tokens") or 0 for r in live),
        "cache_hits": sum(1 for r in records if r["cache_hit"]),
    }
    summary["latency_ms"] = {
        "p50": lat[len(lat) // 2],
        "p95": lat[min(len(lat) - 1, int(len(lat) * 0.95))],
        "p99": lat[min(len(lat) - 1, int(len(lat) * 0.99))],
        "max": lat[-1],
    }
    return summary


# --- printing ----------------------------------------------------------------

def report(summary: dict, header: dict | None = None) -> None:
    if header:
        print("\n%s  %s  temp %s  seed %s"
              % (header.get("prompt_version"), header.get("model"),
                 header.get("temperature"), header.get("seed")))
    print("рядків %d   оцінено %d   збоїв %d   полагоджено %d"
          % (summary["rows"], summary["scored"], summary["failures"],
             summary["repaired"]))
    print("\n%-12s %9s %8s %8s %8s   %s"
          % ("поле", "F1 core", "F1 all", "accuracy", "базова",
             "найчастіша плутанина"))
    for field, block in summary["fields"].items():
        conf = block["top_confusions"]
        first = ("%s->%s x%d" % (conf[0]["gold"], conf[0]["pred"], conf[0]["n"])
                 if conf else "-")
        core = block["macro_f1_core"]
        print("%-12s %9s %8.3f %8.3f %8.3f   %s"
              % (field, "%.3f" % core if core is not None else "н/д",
                 block["macro_f1_all"], block["accuracy"],
                 block["majority_baseline"]["accuracy"], first))
    if summary["headline"] is None:
        print("\nГОЛОВНЕ ЧИСЛО: н/д — жоден клас не набрав n>=%d. На такому "
              "прогоні читай accuracy і лічильники, не середні." % REPORTABLE_N)
    else:
        print("\nГОЛОВНЕ ЧИСЛО (середнє F1 core по трьох полях): %.3f"
              % summary["headline"])
        print("   %s" % RESOLUTION_NOTE)
    print("усі три поля разом: %.3f" % summary["all_three_exact"])
    esc = summary["escalation"]
    print("ескалація: знайдено %d з %d, зайвих %d"
          % (esc["found"], esc["gold"],
             max(0, esc["predicted"] - esc["found"])))
    if summary["failures_by_kind"]:
        print("збої за типом: %s" % ", ".join(
            "%s %d" % kv for kv in sorted(summary["failures_by_kind"].items())))
    ev = summary["evidence_invented"]
    print("цитата не дослівна: %d з %d" % (ev["n"], ev["checked"]))
    sc = summary["self_contradiction"]
    if sc["checked"]:
        print("суперечить власному переліку фактів: %d з %d"
              % (sc["n"], sc["checked"]))
        for c in sc["cases"][:5]:
            print("   %-18s факти %s -> має бути %s, сказала %s"
                  % (c["id"], c["facts"] or "[]", c["implies"], c["said"]))
    print("порушень таблиці:   %d" % summary["table_violations"]["n"])
    for c in summary["table_violations"]["cases"]:
        print("   %-18s %s" % (c["id"], c["why"]))

    print("\n-- по класах (n>=%d числом, менше — лічильником)" % REPORTABLE_N)
    for field, block in summary["fields"].items():
        print("   %s" % field)
        for lab, v in sorted(block["per_class"].items(),
                             key=lambda kv: -kv[1]["support"]):
            if v["support"] >= REPORTABLE_N:
                print("      %-28s F1 %.3f  P %.3f  R %.3f  n=%-4d "
                      "передбачено %d"
                      % (lab, v["f1"], v["precision"], v["recall"],
                         v["support"], v["predicted"]))
            else:
                rare = block["rare_classes"][lab]
                print("      %-28s %d з %d правильно, передбачено %d   "
                      "(n<%d, відсоток не звітний)"
                      % (lab, rare["correct"], rare["support"],
                         rare["predicted"], REPORTABLE_N))

    print("\n-- по мовах (усі три поля разом)")
    for lang, v in sorted(summary["by_language"].items(),
                          key=lambda kv: -kv[1]["n"]):
        if not v["n"]:
            continue
        print("   %-16s n=%-4d %.3f" % (lang, v["n"], v["all_three_exact"]))
    print("-- по наборах")
    for s, v in summary["by_set"].items():
        if v["n"]:
            print("   %-16s n=%-4d %.3f" % (s, v["n"], v["all_three_exact"]))

    c = summary["cost"]
    print("\nціна: $%.4f за прогін   $%.6f за тікет   $%.2f за 10k"
          % (c["total_usd"], c["per_ticket_usd"], c["per_10k_usd"]))
    print("токени: %s вхідних (%s з кешу провайдера), %s вихідних"
          % (format(c["input_tokens"], ","),
             format(c["cached_input_tokens"], ","),
             format(c["output_tokens"], ",")))
    lat = summary["latency_ms"]
    print("латентність: p50 %d, p95 %d, p99 %d, макс %d мс"
          % (lat["p50"], lat["p95"], lat["p99"], lat["max"]))


# --- entry -------------------------------------------------------------------

def spread_report(summaries: list[dict]) -> dict:
    """Mean and range of the same measurement repeated, and the promotion rule.

    A version is not better because its number is higher. Temperature 0 is not
    determinism, and the first pass has the receipt: one prompt version scored
    68-80% across four runs of the same set, because the provider routed the
    requests across replicas. Our model has a single endpoint and accepts a
    seed, so the range should be far smaller - but "should be" is not a
    measurement, which is the whole point of this function.

    THE RULE: a new version counts as better only when the gap between the two
    MEANS exceeds the larger of the two RANGES. Anything smaller is the same
    version twice.
    """
    def field_vals(field):
        return [s["fields"][field]["macro_f1_core"] for s in summaries
                if s["fields"][field]["macro_f1_core"] is not None]

    out = {"runs": len(summaries), "fields": {}}
    heads = [s["headline"] for s in summaries if s["headline"] is not None]
    if not heads:
        print("\n-- розмах: н/д, жоден прогін не дав оцінюваних класів "
              "(набір замалий). Розмах рахується на повному наборі.")
        return {"runs": len(summaries), "note": "no scorable classes"}
    out["headline"] = {"mean": statistics.fmean(heads), "min": min(heads),
                       "max": max(heads), "range": max(heads) - min(heads),
                       "values": heads}
    for field in ("category", "priority", "next_step"):
        v = field_vals(field)
        if not v:
            out["fields"][field] = {"note": "н/д"}
            continue
        out["fields"][field] = {"mean": statistics.fmean(v), "min": min(v),
                                "max": max(v), "range": max(v) - min(v),
                                "values": v}
    exact = [s["all_three_exact"] for s in summaries]
    out["all_three_exact"] = {"mean": statistics.fmean(exact),
                              "range": max(exact) - min(exact)}
    fails = [s["failures"] for s in summaries]
    out["failures"] = {"min": min(fails), "max": max(fails)}
    out["promotion_rule"] = (
        "версія вважається кращою лише якщо різниця середніх перевищує "
        "більший із двох розмахів; на цьому прогоні розмах головного числа "
        "%.3f" % out["headline"]["range"])

    print("\n-- розмах по %d повторах" % len(summaries))
    print("   %-14s %8s %8s %8s %8s" % ("", "середнє", "мін", "макс", "розмах"))
    print("   %-14s %8.3f %8.3f %8.3f %8.3f"
          % ("ГОЛОВНЕ", out["headline"]["mean"], out["headline"]["min"],
             out["headline"]["max"], out["headline"]["range"]))
    for field, v in out["fields"].items():
        if "mean" not in v:
            print("   %-14s %8s" % (field, "н/д"))
            continue
        print("   %-14s %8.3f %8.3f %8.3f %8.3f"
              % (field, v["mean"], v["min"], v["max"], v["range"]))
    print("   збоїв: від %d до %d" % (out["failures"]["min"],
                                      out["failures"]["max"]))
    print("   %s" % out["promotion_rule"])
    return out


LEDGER = ROOT / "data" / "runs" / "eval_results.csv"

LEDGER_COLS = [
    "дата", "промпт", "модель", "набір", "рядків", "оцінено", "збоїв",
    "порушень таблиці", "цитата вигадана", "суперечність фактів",
    "головне F1core", "F1core катег", "F1core пріор", "F1core крок",
    "acc катег", "acc пріор", "acc крок", "базова катег", "базова пріор",
    "базова крок", "усі три", "ескал знайдено", "ескал усього",
    "$ за тікет", "$ за 10k", "токени вх", "токени вих", "з кешу",
    "p50 мс", "p95 мс", "p99 мс", "прогін",
]


def append_ledger(summary: dict, header: dict, run_name: str) -> Path:
    """One row per run in data/runs/eval_results.csv, keyed by the run file.

    A ledger and not a report: every version and every model lands here in the
    same columns, so the prompt evolution IS this file sorted by date, and a
    model comparison is a filter on it. Re-scoring an existing run REPLACES its
    row rather than adding a second one - otherwise a change to the metric code
    would leave two contradictory rows for one measurement and no way to tell
    which is current.

    Semicolons and UTF-8 with a BOM, like every other csv here, because Excel on
    a Ukrainian locale opens comma-separated UTF-8 as one mojibake column.
    """
    def num(v, digits=3):
        return "" if v is None else ("%.*f" % (digits, v)).replace(".", ",")

    f = summary["fields"]
    row = {
        "дата": header.get("started_at", ""),
        "промпт": header.get("prompt_version", ""),
        "модель": header.get("model", ""),
        "набір": header.get("set", ""),
        "рядків": summary["rows"],
        "оцінено": summary["scored"],
        "збоїв": summary["failures"],
        "порушень таблиці": summary["table_violations"]["n"],
        "цитата вигадана": summary["evidence_invented"]["n"],
        "суперечність фактів": (summary["self_contradiction"]["n"]
                                if summary["self_contradiction"]["checked"]
                                else ""),
        "головне F1core": num(summary["headline"]),
        "F1core катег": num(f["category"]["macro_f1_core"]),
        "F1core пріор": num(f["priority"]["macro_f1_core"]),
        "F1core крок": num(f["next_step"]["macro_f1_core"]),
        "acc катег": num(f["category"]["accuracy"]),
        "acc пріор": num(f["priority"]["accuracy"]),
        "acc крок": num(f["next_step"]["accuracy"]),
        "базова катег": num(f["category"]["majority_baseline"]["accuracy"]),
        "базова пріор": num(f["priority"]["majority_baseline"]["accuracy"]),
        "базова крок": num(f["next_step"]["majority_baseline"]["accuracy"]),
        "усі три": num(summary["all_three_exact"]),
        "ескал знайдено": summary["escalation"]["found"],
        "ескал усього": summary["escalation"]["gold"],
        "$ за тікет": num(summary["cost"]["per_ticket_usd"], 6),
        "$ за 10k": num(summary["cost"]["per_10k_usd"], 2),
        "токени вх": summary["cost"]["input_tokens"],
        "токени вих": summary["cost"]["output_tokens"],
        "з кешу": summary["cost"]["cached_input_tokens"],
        "p50 мс": summary["latency_ms"]["p50"],
        "p95 мс": summary["latency_ms"]["p95"],
        "p99 мс": summary["latency_ms"]["p99"],
        "прогін": run_name,
    }

    rows = []
    if LEDGER.exists():
        with io.open(LEDGER, encoding="utf-8-sig") as fh:
            rows = [r for r in csv.DictReader(fh, delimiter=";")
                    if r.get("прогін") != run_name]
    rows.append(row)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with io.open(LEDGER, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=LEDGER_COLS, delimiter=";",
                           quoting=csv.QUOTE_ALL, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in LEDGER_COLS})
    return LEDGER


def ticket_texts() -> dict[str, str]:
    """id -> ticket text, rejoined from the sets.

    The run file deliberately does not carry the text: 432 tickets duplicated
    into every run would make the ledger mostly copies of the corpus, and the id
    is a join key that cannot go stale.
    """
    out = {}
    for name in ("fewshot", "dev", "golden", "synthetic"):
        path = SETS / f"{name}_v1.json"
        if not path.exists():
            continue
        for r in json.loads(path.read_text(encoding="utf-8")):
            out[r["id"]] = ticket_text(r)
    return out


def write_table(records: list[dict], path: Path, header: dict) -> None:
    """The brief's own artifact: input -> expected -> actual -> pass/fail.

        «таблицю input → expected → actual → pass/fail»

    Markdown, because it is read rather than computed over, and the failures are
    put FIRST: a reader who opens 250 rows of correct answers learns nothing, and
    the rows that disagree are the error analysis the same sentence asks for.
    The ticket text is truncated to 160 characters - enough to see what the
    model was looking at, and the full text is one join away by id.
    """
    def cell(rec, key):
        v = rec.get(key)
        return " / ".join((v or {}).get(f, "") for f in
                          ("category", "priority", "next_step")) if v else "—"

    def clip(s, n):
        return " ".join((s or "").split())[:n].replace("|", "\\|")

    texts = ticket_texts()
    rows = sorted(records, key=lambda r: (r["ok"] and r["gold"] == r["pred"],
                                          r["набір"], r["id"]))
    passed = sum(1 for r in records if r["ok"] and r["gold"] == r["pred"])
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write("# input -> expected -> actual -> pass/fail\n\n")
        fh.write("%s · %s · temp %s · seed %s\n\n"
                 % (header.get("prompt_version"), header.get("model"),
                    header.get("temperature"), header.get("seed")))
        fh.write("pass %d / %d (%.1f%%). Розбіжності зверху.\n\n"
                 % (passed, len(records), 100.0 * passed / max(1, len(records))))
        fh.write("Порядок трійки: категорія / пріоритет / крок.\n\n")
        fh.write("| id | набір | мова | input | expected | actual | pass | "
                 "цитата моделі |\n")
        fh.write("|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            ok = "PASS" if r["ok"] and r["gold"] == r["pred"] else "FAIL"
            note = "" if r["ok"] else " · %s" % clip(r.get("error"), 60)
            fh.write("| `%s` | %s | %s | %s | %s | %s | %s%s | %s |\n"
                     % (r["id"], r["набір"], r["мова"] or "-",
                        clip(texts.get(r["id"], ""), 200) or "(порожньо)",
                        cell(r, "gold"), cell(r, "pred"), ok, note,
                        clip(r.get("evidence"), 80)))


def read_run(path: Path) -> tuple[dict, list[dict]]:
    header, records = {}, []
    for line in io.open(path, encoding="utf-8"):
        obj = json.loads(line)
        if obj.get("kind") == "header":
            header = obj
        else:
            records.append(obj)
    return header, records


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--set", default="dev",
                    choices=["dev", "golden", "synthetic", "eval", "fewshot"])
    ap.add_argument("--prompt", default=None, help="версія промпту, типово з .env")
    ap.add_argument("--model", default=None, help="перекрити модель версії")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--cache", action="store_true",
                    help="читати з кешу: дешево для повторів, але прогін "
                         "з кешу показує нульову ціну і нульовий розкид")
    ap.add_argument("--score", default=None, metavar="RUN",
                    help="перерахувати метрики зі збереженого прогону")
    ap.add_argument("--show", type=int, nargs="?", const=-1, default=0,
                    metavar="N",
                    help="друкувати повний обмін: --show 5 для перших п'яти, "
                         "--show без числа для всього набору")
    ap.add_argument("--dry-run", action="store_true",
                    help="показати системний промпт і перші тікети так, як вони "
                         "пішли б у модель, і зупинитись. Без запитів і витрат")
    ap.add_argument("--repeats", type=int, default=1,
                    help="прогнати набір кілька разів і показати розмах; "
                         "версію не можна називати кращою, якщо приріст "
                         "менший за розмах")
    args = ap.parse_args()

    if args.score:
        header, records = read_run(Path(args.score))
        summary = score(records)
        report(summary, header)
        out = Path(args.score).with_suffix(".summary.json")
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        table = Path(args.score).with_suffix(".table.md")
        write_table(records, table, header)
        ledger = append_ledger(summary, header, Path(args.score).name)
        print("\nзведення: %s\nтаблиця:  %s\nтаблиця метрик: %s"
              % (out, table, ledger))
        return

    settings = Settings()
    prompt = PROMPTS[args.prompt or settings.prompt_version]
    rows = load_set(args.set)
    if args.limit:
        rows = rows[:args.limit]
    if args.dry_run:
        model = args.model or prompt.model
        show_request(prompt, model, settings)
        for row in rows[:max(1, args.show or 3)]:
            text = ticket_text(row)
            gold = row["розмітка"]
            print("\n" + "-" * 78)
            print("USER  %s  (%s, %s, %d знаків)"
                  % (row["id"], row["набір"], row["мова"] or "-", len(text)))
            print("-" * 78)
            print(text)
            print("-" * 78)
            print("очікуємо  %s / %s / %s"
                  % (gold["категорія"], gold["пріоритет"],
                     gold["наступний крок"]))
        print("\nсухий прогін: жодного запиту не надіслано, витрат нуль.")
        return

    if args.cache and args.repeats > 1:
        raise SystemExit("--cache з --repeats дає нульовий розмах за побудовою: "
                         "другий прогін читає відповіді першого. Оберіть одне.")
    cache = Cache(settings.cache_path) if args.cache else None

    settings.runs_dir.mkdir(parents=True, exist_ok=True)
    slug = (args.model or prompt.model).replace("/", "-")
    print("прогін: %s на %s (%d рядків), %d потоків, повторів %d"
          % (prompt.version, args.set, len(rows), args.workers, args.repeats))

    summaries, paths = [], []
    for attempt in range(args.repeats):
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = (settings.runs_dir
                    / f"{stamp}_{prompt.version}_{slug}_{args.set}.jsonl")
        if args.repeats > 1:
            print("\n-- повтор %d з %d" % (attempt + 1, args.repeats))
        if args.show != 0 and attempt == 0:
            show_request(prompt, args.model or prompt.model, settings)
        records = run_set(rows, prompt, settings, args.model, args.workers,
                          cache, out_path, show=args.show, set_name=args.set)
        summary = score(records)
        header, _ = read_run(out_path)
        out_path.with_suffix(".summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        write_table(records, out_path.with_suffix(".table.md"), header)
        append_ledger(summary, header, out_path.name)
        summaries.append(summary)
        paths.append(out_path)

    report(summaries[-1], read_run(paths[-1])[0])
    if args.repeats > 1:
        spread = spread_report(summaries)
        combined = paths[-1].with_name(paths[-1].stem + "_spread.json")
        combined.write_text(json.dumps(
            {"runs": [p.name for p in paths], "spread": spread},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print("розмах: %s" % combined)
    for p in paths:
        print("прогін: %s  (+ .summary.json, .table.md)" % p)



if __name__ == "__main__":
    main()
