"""Three questions the grid table cannot answer by itself.

    python eval/analyse.py

DOES THE WINNER SURVIVE A DIFFERENT ANSWER KEY
    The key is built by a model, and the engineer has not reviewed it yet. So
    before any of these numbers is quoted, the same fourteen cells are scored
    against a key built independently by a second model, and the two orderings
    are compared. If a design only wins under one key, it has not won.

WHERE IS THE LINE BELOW WHICH THE ASSISTANT MUST SAY NOTHING
    The assignment asks what the assistant does when it cannot answer. That
    line is a score, and it can only be drawn by looking at scores on tickets
    the base genuinely cannot close next to scores on tickets it can. Both are
    recorded per cell.

DOES THE SECTION INDEX GET THE RAIL RIGHT
    Cancelling is done in a different place depending on where the purchase was
    made, and the article says so in six numbered sections. Only the section
    index can return one of them. So: when the ticket came from the App Store,
    did the App Store section come back, or the Google Play one - which would
    be a confidently wrong instruction rather than a miss.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "eval" / "results"
CANCEL = "hc-28900802305297"
# Section index -> the rail that section is about, read off the article's own
# numbered headings. The web rails are not decided by the store the review was
# posted to, so only these two are scored.
RAIL_SECTION = {"appstore": f"{CANCEL}#1", "googleplay": f"{CANCEL}#3"}


def load(stamp: str) -> dict:
    return json.loads((RESULTS / f"retrieval_{stamp}.json").read_text(
        encoding="utf-8"))


def key(cell: dict) -> tuple:
    return cell["variant"], cell["method"], cell["encoder"]


def ordering(run: dict, metric: str) -> list[tuple]:
    return [key(c) for c in sorted(run["cells"], key=lambda c: -c[metric])]


def kendall(a: list, b: list) -> float:
    """Rank agreement between two orderings of the same items, -1 to 1."""
    position = {item: i for i, item in enumerate(b)}
    concordant = discordant = 0
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            left = position[a[i]] - position[a[j]]
            concordant += left < 0
            discordant += left > 0
    total = concordant + discordant
    return (concordant - discordant) / total if total else 0.0


def robustness(runs: dict[str, dict]) -> None:
    names = list(runs)
    a, b = runs[names[0]], runs[names[1]]
    print(f"=== СТІЙКІСТЬ ПОРЯДКУ: {names[0]} проти {names[1]} ===")
    for metric in ("lenient@5", "strict@5", "mrr@5"):
        oa, ob = ordering(a, metric), ordering(b, metric)
        tau = kendall(oa, ob)
        same_top = oa[0] == ob[0]
        print(f"  {metric:<11} tau={tau:+.3f}   той самий переможець: "
              f"{'так' if same_top else 'НІ'}   {'-'.join(oa[0][:2])}"
              f" {oa[0][2].split('/')[-1]}")
    cells_a = {key(c): c for c in a["cells"]}
    print()
    print(f"  {'клітинка':<46} {'lenient@5':>10} {'lenient@5':>10} {'дельта':>8}")
    print(f"  {'':<46} {names[0][:10]:>10} {names[1][:10]:>10}")
    for c in sorted(b["cells"], key=lambda c: -c["lenient@5"])[:6]:
        k = key(c)
        before = cells_a[k]["lenient@5"]
        name = f"{k[0]} {k[1]} {k[2].split('/')[-1]}"
        print(f"  {name:<46} {before:>10.3f} {c['lenient@5']:>10.3f} "
              f"{c['lenient@5'] - before:>+8.3f}")


def abstention(run: dict, cell: tuple) -> None:
    c = next(x for x in run["cells"] if key(x) == cell)
    answerable = [q["top_score"] for q in c["per_query"]]
    none = [q["top_score"] for q in c["no_answer"]]
    print()
    print(f"=== ПОРІГ ВІДМОВИ: {cell[0]} {cell[1]} "
          f"{cell[2].split('/')[-1]} ===")
    if not none:
        print("  немає жодного тікета без відповіді - поріг не з чого брати")
        return
    qs = statistics.quantiles(answerable, n=20)
    print(f"  тікети З відповіддю ({len(answerable)}): "
          f"медіана {statistics.median(answerable):.3f}, "
          f"5-й перцентиль {qs[0]:.3f}, мін {min(answerable):.3f}")
    print(f"  тікети БЕЗ відповіді ({len(none)}): "
          f"медіана {statistics.median(none):.3f}, "
          f"макс {max(none):.3f}, мін {min(none):.3f}")
    print()
    print(f"  {'поріг':>7} {'відсіяно без відповіді':>24} "
          f"{'втрачено з відповіддю':>23}")
    for t in sorted({round(x, 2) for x in none} |
                    {round(qs[0], 2), round(statistics.median(none), 2)}):
        caught = sum(1 for s in none if s < t)
        lost = sum(1 for s in answerable if s < t)
        print(f"  {t:>7.2f} {caught:>10}/{len(none):<13} "
              f"{lost:>10}/{len(answerable):<12}")
    print("  (поріг корисний лише там, де він ловить відмови дешевше,")
    print("   ніж викидає справжні відповіді - на 5 випадках це вказівка,")
    print("   а не калібрування)")


def rail(run: dict) -> None:
    print()
    print("=== ТОЧНІСТЬ РЕЙЛА (тільки section) ===")
    for c in run["cells"]:
        if c["variant"] != "section" or c["method"] != "dense":
            continue
        right = wrong = silent = 0
        for q in c["per_query"]:
            want = RAIL_SECTION.get(q["store"])
            if not want or q["rail_uncertain"] or CANCEL not in q["returned"]:
                continue
            got = [ch for ch in q["chunks"] if ch.startswith(CANCEL)]
            if not got:
                silent += 1
            elif got[0] == want:
                right += 1
            else:
                wrong += 1
        total = right + wrong + silent
        if not total:
            continue
        name = c["encoder"].split("/")[-1]
        print(f"  {name:<28} правильна секція {right:>3}/{total:<3} "
              f"({right / total:.0%})   не та {wrong:<3}   немає секції {silent}")
    print("  (рахується лише там, де стаття про скасування взагалі повернулась")
    print("   і магазин відомий; тікети з rail_uncertain виключені)")


def main() -> None:
    stamps = sorted(p.stem.replace("retrieval_", "")
                    for p in RESULTS.glob("retrieval_*.json"))
    runs = {}
    for stamp in stamps[-2:]:
        run = load(stamp)
        runs[run["gold"].replace("gold_", "").replace(".csv", "")] = run
    if len(runs) == 2:
        robustness(runs)
    winner = ("article", "dense", "openai/text-embedding-3-small")
    for name, run in runs.items():
        abstention(run, winner)
        break
    rail(list(runs.values())[0])


if __name__ == "__main__":
    main()
