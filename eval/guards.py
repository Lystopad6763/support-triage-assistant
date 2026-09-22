"""Test the seven policy guards against phrasings that must and must not fire.

    python eval/guards.py

WHY THIS FILE EXISTS
    The guards in app/assist.py were wrong twice, in the same direction both
    times. First they matched the TOPIC: a reply saying "please do not request
    a chargeback" - which is exactly what pol-15 asks for - was reported as
    violating pol-15, three times in twenty drafts. Negation-awareness fixed
    those three and left a fourth, because "initiating a chargeback may result
    in the termination of your account" discourages it without one negative
    word. And the refund-window guard flagged "at least 15 business days",
    which is the sentence pol-14 is made of.

    A guard that fires on correct behaviour is worse than no guard. It is read
    for a week and ignored afterwards, and then it is not there on the draft
    that needed it.

    So both directions are tested, and the second list matters more: the cost
    of a false alarm is that the guard stops being read at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import assist                                 # noqa: E402

# Each of the seven, phrased the way a model actually phrases it when it gets
# this wrong - not the way the rule is written.
MUST_FIRE = [
    ("You can request a chargeback from your bank.", "suggests a chargeback"),
    ("File a chargeback with your bank to get the money back.",
     "suggests a chargeback"),
    ("We recommend a chargeback if we have not replied in a week.",
     "suggests a chargeback"),
    ("We will issue your refund from the App Store.",
     "promises an App Store refund"),
    ("Your refund will arrive in 3 business days.",
     "promises a short refund window"),
    ("The refund takes a few days.", "promises a short refund window"),
    ("We will refund the credits to your balance.", "promises credits back"),
    ("Please delete the app to cancel your subscription.",
     "says deleting the app cancels"),
    ("You are eligible for a refund.", "decides refund entitlement"),
    ("All our advisors are verified professionals.",
     "claims advisors are screened"),
]

# Sentences a correct reply contains. Every one of these is either quoted from
# the policies or is the standard way of obeying them.
MUST_NOT_FIRE = [
    "Please do not initiate a chargeback, as this can close your account.",
    "Please be advised that initiating a chargeback may result in the "
    "immediate termination of your account.",
    "Deleting the app does not cancel your subscription, trial or "
    "introductory offer.",
    "A confirmed refund takes at least 15 business days to appear.",
    "We will respond to your inquiry within 15 business days.",
    "App Store refunds are decided by Apple, so we cannot issue one here.",
    "Refund requests are reviewed individually by our support team.",
    "Balance units are not refundable.",
    "Our advisors are independent practitioners.",
    "To cancel, open Settings, tap your name, then Subscriptions.",
    # The shape an empathetic reply takes by itself: the misconception is
    # repeated so it can be corrected, and the correction comes after it.
    "It sounds like you were charged because you believed uninstalling the "
    "app would end your trial, but unfortunately, that does not cancel the "
    "subscription.",
    "Many people assume that removing the app stops the billing; it does not.",
]


def scan(text: str) -> list[str]:
    """Literally the function the assistant runs, not a copy of it.

    A test that reimplements what it tests can pass while production fails, so
    this imports rather than reproduces. Labels carry their policy - "suggests
    a chargeback (pol-15)" - and the expectations below are matched as
    prefixes.
    """
    return assist.violations(text)


def main() -> None:
    missed = []
    for text, expected in MUST_FIRE:
        got = scan(text)
        if not any(g.startswith(expected) for g in got):
            missed.append((text, expected, got))

    false_alarms = []
    for text in MUST_NOT_FIRE:
        got = scan(text)
        if got:
            false_alarms.append((text, got))

    print(f"must fire     : {len(MUST_FIRE) - len(missed)}/{len(MUST_FIRE)}")
    for text, expected, got in missed:
        print(f"    MISSED [{expected}] {text}")
        print(f"           got {got}")

    print(f"must not fire : "
          f"{len(MUST_NOT_FIRE) - len(false_alarms)}/{len(MUST_NOT_FIRE)}")
    for text, got in false_alarms:
        print(f"    FALSE ALARM {got}")
        print(f"                {text}")

    if missed or false_alarms:
        raise SystemExit(f"\n{len(missed)} missed, {len(false_alarms)} false "
                         f"alarms - the guards are not ready")
    print("\nboth directions clean")


if __name__ == "__main__":
    main()
