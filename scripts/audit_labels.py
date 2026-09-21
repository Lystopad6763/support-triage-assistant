"""Find labels that contradict the taxonomy's own rules.

    python scripts/audit_labels.py                # both sets
    python scripts/audit_labels.py --set golden

Six tickets on dev were classified "wrong" by every run of v5, and four of them
turned out to be labelling errors of mine - the model was applying my written
rule better than I had. A rubric that a human applies inconsistently is not a
rubric, so the rules are checked mechanically here instead of by re-reading.

Each check is a NECESSARY CONDITION of the label, read off the taxonomy:

    unauthorized_charge   needs NO prior payment. A trial, a 1-dollar reading or
                          a starting payment anywhere in the text contradicts it.
    cancellation_failed   the taxonomy says "cannot find OR complete
                          cancellation, or cancelled and was billed anyway", so
                          either a cancellation action or an inability to cancel
                          satisfies it. Only a deletion with neither does not:
                          deleting an app stops no subscription.
                          (The first version of this check demanded a completed
                          action, the narrower wording from the v5 prompt, and
                          flagged 23 correct labels. The prompt is what is wrong
                          there, not the labels.)
    trial_converted       needs a small starting payment or a trial, and a larger
                          charge that followed it.
    refund_request        is the fallback: it needs the absence of an identifiable
                          cause, so a trial, a cancellation attempt or a
                          mis-priced charge in the text contradicts it.
    pricing_unclear       needs a price that was presented and then not honoured.

A flag is not a verdict. It says the text does not contain what the label
requires, and that the row needs a human decision - printed with the evidence so
that decision is quick.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Multilingual on purpose: a quarter of both sets is not in English, and an
# English-only check would silently pass every one of those rows.
# Stems take \w*, whole words take \b...\b. A boundary immediately after a stem
# is the bug that made the ticket-selection script miss "charged" and
# "cancelled", and it hit this file too: d[ée]sabonn could never match
# "desabonnes". Half of the 31 first flags were that, or a missing Japanese verb.
STARTING_PAYMENT = re.compile(
    r"(\b(1|one|2|3|5)\s*(\$|usd|dollar|euro|eur|£|pound|zl|real|reais|lei|lira)"
    r"|(\$|usd|eur|€|£|r\$)\s*(1|2|3|5)([.,]\d{2})?\b"
    r"|\b0[.,]50\b|\b0[.,]99\b"          # 0.99, not the .99 inside 49.99
    r"|free\s*trial|trial|prueba|probe|essai|試用|试用|トライアル|무료|deneme"
    r"|\d[- ]day free|three[- ]day free|free \d[- ]day"
    r"|1\s*(dolar|dólar|달러|евро|美元|€|\$)"
    r"|small purchase|pequena compra|petit achat|kleine\w* (kauf|betrag)"
    r"|\bstarter\b|initial offer|first payment|erste\w* zahlung"
    r"|اشتراك تجريبي|1 دولار)", re.I)

# A cancellation that was DONE. Intent ("I need to cancel") is deliberately not
# here - wanting to cancel is not a failed cancellation.
CANCEL_ACTION = re.compile(
    r"(cancell?ed\b|cancell?ing\b|have cancell?ed|unsubscrib\w*|un-?subscrib\w*"
    r"|cancellation instructions|cancell?ed my subscription|desuscrib\w*"
    r"|cancelad\w*|cancelei|anul\w*|annull\w*|k[üu]ndig\w*|gek[üu]ndigt"
    r"|d[ée]sabonn\w*|r[ée]sili\w*|disdett\w*|解約|退会|取消订阅|取消訂閱|已取消"
    r"|해지|취소했|отменил\w*|скасував|отписал\w*|iptal ed\w*|iptal ett\w*|ألغيت"
    r"|asked (them |support )?to cancel|requested cancellation"
    r"|sent a request to cancel|request(ed)? to cancel)", re.I)

DELETION_ONLY = re.compile(
    r"(deleted|deleting|uninstall\w*|removed the app|sildim|kaldırdım|borr[ée]\w*"
    r"|gel[öo]scht|supprim[ée]\w*|삭제|删除|удалил\w*)", re.I)

# Cannot find or complete it - which the taxonomy counts as cancellation_failed
# just as much as a completed attempt.
CANNOT_CANCEL = re.compile(
    r"(not there to cancel|nothing there|no (clear )?(way|option|tab|button|link)"
    r" to (cancel|unsubscribe)|can(no|')?t (find|cancel|unsubscribe)"
    r"|cannot (find|cancel|unsubscribe)|couldn'?t find|impossible to cancel"
    r"|(too )?hard( for \w+)? to cancel|figure out how to cancel"
    r"|trying to (figure|find)"
    r"|hunt\w* thr(u|ough)|don'?t have a cancell?ation|no cancell?ation option"
    r"|link .{0,20}broken|freezes when you try|nowhere to cancel"
    r"|취소.{0,12}(없|못|어디)|찾을 수 없|어디에도|no aparece|no encuentro"
    r"|nicht finden|keinen? (klaren )?weg|introuvable|impossible de (se )?"
    r"d[ée]sabonn|non riesco|n[ãa]o consigo|iptal ed[ei]m[ie]yor"
    r"|صعوبة في إلغاء|لا يمكن"
    r"|no me sale|por ning[úu]n lado|nessuna opzione)", re.I)

# "A larger charge followed" is satisfied by an amount of ten or more OR by a
# charge verb with no amount at all: the corpus says "I have been debited" as
# often as it says "$45", and a missing number is not a missing charge.
BIGGER_CHARGE = re.compile(
    r"(\b[1-9]\d{1,6}([.,]\d{1,2})?\b"
    r"|charged|debited|billed|deducted|taken from my|prélev\w*|débit\w*"
    r"|abgebucht|einzug|cobrad\w*|cobrança|descont\w*|addebit\w*|扣款|扣了|課金"
    r"|결제|청구|списал\w*|خصم)", re.I)

PRICE_PRESENTED = re.compile(
    r"(free|gratis|gratuit|kostenlos|gr[aá]tis|ücretsiz|무료|免费|免費|無料"
    r"|advertised|said it was|displayed|shown as|per month|monthly|upsell"
    r"|pay extra|3[- ]day|three[- ]day|nicht klar|no (era|estaba) claro"
    r"|n[ãa]o (estava|era) claro|لم يكن واضح|不清楚|不明確"
    r"|initial offer|erste\w* zahlung|ungefragt|ungewollt)", re.I)

CHECKS = {
    "unauthorized_charge": [
        ("a starting payment or trial is described, so a prior purchase exists",
         lambda text: bool(STARTING_PAYMENT.search(text))),
    ],
    "cancellation_failed": [
        ("neither a cancellation action nor an inability to cancel is in the text",
         lambda text: not CANCEL_ACTION.search(text) and not CANNOT_CANCEL.search(text)),
        ("only a deletion, which cancels nothing, and no attempt to cancel",
         lambda text: (bool(DELETION_ONLY.search(text))
                       and not CANCEL_ACTION.search(text)
                       and not CANNOT_CANCEL.search(text))),
    ],
    "trial_converted": [
        ("no starting payment or trial in the text",
         lambda text: not STARTING_PAYMENT.search(text)),
        ("no larger charge after the starting payment",
         lambda text: not BIGGER_CHARGE.search(text)),
    ],
    "refund_request": [
        ("a trial or starting payment IS described, so the cause is identifiable "
         "and this is not the fallback label",
         lambda text: bool(STARTING_PAYMENT.search(text))),
        ("a cancellation action or a broken cancellation IS described, so the "
         "cause is identifiable",
         lambda text: bool(CANCEL_ACTION.search(text) or CANNOT_CANCEL.search(text))),
    ],
    "pricing_unclear": [
        ("no presented price or promise in the text to compare the charge against",
         lambda text: not PRICE_PRESENTED.search(text)),
    ],
}


# Flags that were looked at and accepted, with the reason. A check that keeps
# reporting a row somebody already decided on trains people to ignore it, so a
# decision is recorded once and the row moves out of the open list. Anything not
# in here is still open.
DECIDED = {
    "as:13540954035":
        "unauthorized_charge kept: a 1-dollar purchase was accepted, but the 77.30 "
        "went through Apple Pay with no Face ID and no confirmation screen, so it "
        "renewed nothing. The check cannot see 'no confirmation step'.",
    "as:14369349630":
        "unauthorized_charge kept: 1.00 and 29.99 were taken in the same moment, "
        "so no trial had elapsed for anything to convert.",
    "gp:104349bb-267":
        "trial_converted kept: the charge is stated but never with an amount "
        "('charges a subscription fee'), which the check cannot verify.",
    "gp:8f7008e4-4ca":
        "unauthorized_charge kept: 0.50 bought a one-off soulmate drawing, not a "
        "trial, nothing was delivered, the account and app were deleted, and 78 "
        "was taken afterwards. A charge that lands after the account is gone "
        "renews nothing.",
    "as:12136193056":
        "cancellation_failed kept: 'I cancel the very next day' and support then "
        "found no subscription to cancel. The check wants a past-tense verb.",
    "gp:fc7472ac-1c1":
        "cancellation_failed kept: the 50 has not been taken yet and the only "
        "thing the writer needs is the way out, which is what gp:1fd14cb2-984 and "
        "gp:e18e8473-db4 in golden are labelled. Intent with no attempt still "
        "means the mechanism has not been completed.",
    "as:13613859375":
        "cancellation_failed kept: the demand is to cancel a repeating 50 charge "
        "and the writer cannot sign back into the account to do it.",
    "as:14304708630":
        "trial_converted kept: a one-off sketch purchase followed by a "
        "subscription charge, with no amount given for the starting payment.",
    "gp:44d651fb-41a":
        "pricing_unclear kept: 13.67 reais was presented and nearly 80 was taken "
        "after a currency conversion. The presented price is a number here, not "
        "the word 'free', which is all the check looks for.",
}


def audit(rows: list[dict]) -> list[dict]:
    flagged = []
    for row in rows:
        label = row["label"]["category"]
        text = row["text"]
        reasons = [why for why, test in CHECKS.get(label, []) if test(text)]
        if reasons:
            flagged.append({"ticket_id": row["ticket_id"], "label": label,
                            "decided": DECIDED.get(row["ticket_id"]),
                            "priority": row["label"]["priority"],
                            "confidence": row["label"]["confidence"],
                            "reasons": reasons, "text": text,
                            "rationale": row["label"]["rationale"]})
    return flagged


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", default=None, choices=["dev", "golden"])
    parser.add_argument("--quiet", action="store_true", help="counts only")
    args = parser.parse_args()

    sets = [args.set] if args.set else ["dev", "golden"]
    everything = []
    for name in sets:
        path = os.path.join(ROOT, "data", "tickets", f"{name}.json")
        with open(path, encoding="utf-8") as handle:
            rows = json.load(handle)
        flagged = audit(rows)
        everything += [dict(f, set=name) for f in flagged]
        opened = [f for f in flagged if not f["decided"]]
        print(f"{name}: {len(flagged)} of {len(rows)} flagged, "
              f"{len(flagged) - len(opened)} already decided, {len(opened)} open")
        if args.quiet:
            continue
        for item in opened:
            print("-" * 78)
            print(f"{item['ticket_id']}  labelled {item['label']} "
                  f"P{item['priority']} (conf {item['confidence']})")
            for reason in item["reasons"]:
                print(f"  ! {reason}")
            print("  text:", " ".join(item["text"].split())[:400])
            print("  mine:", item["rationale"][:220])

    out = os.path.join(ROOT, "eval", "results", "label_audit.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(everything, handle, ensure_ascii=False, indent=2)
    print(f"\n{len(everything)} flagged -> eval/results/label_audit.json")


if __name__ == "__main__":
    main()
