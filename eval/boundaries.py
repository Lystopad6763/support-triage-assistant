"""Test the pre-pass in both directions, and against the real 430.

    python eval/boundaries.py

WHY THE SECOND LIST IS THE IMPORTANT ONE
    A net that catches figures of speech gets switched off, and a net that is
    switched off is not there on the ticket that needed it. "I was dying to
    see my reading", "this app is killing me", "my daughter recommended it" -
    all of them contain the words and none of them is the thing.

    So the false-alarm list is longer than the must-fire list on purpose, and
    a single hit in it fails the run.

AND WHY IT IS ALSO RUN OVER ALL 430
    A rate is the only way to see a net that is too wide. If crisis fired on
    thirty of 430 real complaints about subscriptions, the list would be
    broken no matter how well it did on invented sentences.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import boundaries                             # noqa: E402

TICKETS = ROOT / "benchmark" / "tickets.csv"

MUST_FIRE = [
    ("I want to die, nothing matters any more.", "crisis"),
    ("You took my last 50 dollars and I do not want to live any more.", "crisis"),
    ("I don't want to live anymore after this.", "crisis"),
    ("There is nothing to live for now.", "crisis"),
    ("Estoy pensando en quitarme la vida.", "crisis"),
    ("Ich will nicht mehr leben.", "crisis"),
    ("Je veux mourir, tout est fini.", "crisis"),
    ("Я не хочу жити після цього.", "crisis"),
    ("죽고 싶어요.", "crisis"),
    ("My daughter used my phone and subscribed.", "minor"),
    ("Mi hija compro la suscripcion sin permiso.", "minor"),
    ("Meine Tochter hat das Abo gekauft.", "minor"),
    ("Tengo 15 años y no puedo cancelar.", "minor"),
    ("Ich bin 16 Jahre alt und habe kein Konto.", "minor"),
    ("I have already filed a chargeback with my bank.", "legal"),
    ("J'ai deja depose une plainte aupres de la DGCCRF.", "legal"),
    ("Ich habe die Verbraucherzentrale eingeschaltet.", "legal"),
    ("My lawyer will contact you.", "legal"),
    ("Abri uma reclamacao no PROCON.", "legal"),
]

# Ordinary complaints that contain the words and none of the meaning.
MUST_NOT_FIRE = [
    "I was dying to see my reading and it never arrived.",
    "This app is killing me with these charges.",
    "My daughter recommended this app to me, and now I regret it.",
    "I am 45 years old and I have never seen a scam like this.",
    "The subscription is 18 euros a month, which I never agreed to.",
    "You have 30 days to refund me before I leave a review.",
    "I will dispute this with my bank if you do not answer.",
    "Court of public opinion, that is where you belong.",
    "I paid 16 dollars for nothing.",
    "My son-in-law told me this app was a scam and he was right.",
    "Deadline was yesterday and still no reading.",
    "It is a killer feature that you cannot cancel anywhere.",
    "My daughter is going to laugh at me for falling for this.",
    "I will take this to the court of public opinion.",
    "My son-in-law works in finance and says this is illegal.",
    # "End it" is what people say about a subscription far more often than
    # about anything else, so the list must not reach for it.
    "I want to end it, this subscription has cost me enough.",
    "I do not want to live with this charge on my card every month.",
]


def main() -> None:
    missed = []
    for text, expected in MUST_FIRE:
        got = boundaries.check(text).flags
        if expected not in got:
            missed.append((text, expected, got))

    false_alarms = []
    for text in MUST_NOT_FIRE:
        got = boundaries.check(text)
        if got.flags:
            false_alarms.append((text, got.flags, got.matched))

    print(f"must fire     : {len(MUST_FIRE) - len(missed)}/{len(MUST_FIRE)}")
    for text, expected, got in missed:
        print(f"    MISSED [{expected}] {text}   got {got}")
    print(f"must not fire : "
          f"{len(MUST_NOT_FIRE) - len(false_alarms)}/{len(MUST_NOT_FIRE)}")
    for text, flags, matched in false_alarms:
        print(f"    FALSE ALARM {flags} {matched}")
        print(f"                {text}")

    rows = list(csv.DictReader(TICKETS.open(encoding="utf-8-sig"),
                               delimiter=";"))
    tally = {"crisis": [], "minor": [], "legal": []}
    for row in rows:
        for flag in boundaries.check(row["original"]).flags:
            tally[flag].append(row["id"])

    print(f"\nover the real {len(rows)}:")
    for flag, ids in tally.items():
        print(f"  {flag:<7} {len(ids):>3}  ({len(ids) / len(rows):.1%})"
              f"  {' '.join(ids[:4])}")

    if missed or false_alarms:
        raise SystemExit(f"\n{len(missed)} missed, {len(false_alarms)} false "
                         f"alarms - the pre-pass is not ready")
    print("\nboth directions clean")


if __name__ == "__main__":
    main()
