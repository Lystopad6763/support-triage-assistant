"""The label vocabulary: what the classifier may return, and why each exists.

WHERE THESE COME FROM
    Not from imagination, and not from Nebula's help centre either. The help
    centre describes a different population of problems than the one people
    actually write about:

        area                    help centre      ticket pool
        Subscriptions & Billing   3 articles           ~79%
        Account Management       13 articles            0.2%
        How to Use               13 articles            ~2%
        Tech Assistance          11 articles            0.7%

    People write publicly about money and privately about everything else. The
    categories below are derived from the 313-row ticket pool that
    scripts/criteria.py selects out of 43,941 collected reviews.

ABOUT THE COUNTS
    They come from the sampling probes in scripts/criteria.py, whose measured
    recall is 69%, so every count is a LOWER BOUND. They are here to show the
    shape of the distribution, not to be quoted as a census. For the four
    rarest categories the window count and the whole-corpus count are both
    given, because a category with 2 rows in the window and 21 in the corpus is
    scarce, not absent.

WHY BILLING SPLITS FIVE WAYS
    One `billing` label would cover ~79% of volume and carry no routing
    information at all. The five splits each route somewhere different: an
    unauthorised charge is a dispute, a cancellation failure is a how-to, a
    converted trial is a policy explanation.

WHAT IS DELIBERATELY NOT A CATEGORY
    A legal threat and distressing content are FLAGS, not categories. A refund
    complaint that threatens a chargeback is still a refund complaint; the
    threat changes the priority and the next step, not the subject. Making
    either a category would let it swallow the ticket's actual topic.

THE STAR RATING IS NOT AN INPUT
    It selects rows for the dataset and never reaches the model. The real
    support form has no star field, so accuracy bought with one would not
    survive deployment.
"""
from __future__ import annotations

from enum import Enum


class Category(str, Enum):
    """What the ticket is about. Exactly one is primary."""

    # --- billing family: the overwhelming majority of volume -------------
    # Three questions, not five: was the charge agreed to, can it be stopped,
    # and is the refund itself the problem.
    SUBSCRIPTION_TRAP = "subscription_trap"
    CANCELLATION_FAILED = "cancellation_failed"
    REFUND_REQUEST = "refund_request"

    # --- the service itself ----------------------------------------------
    SERVICE_NOT_DELIVERED = "service_not_delivered"
    CONTENT_QUALITY = "content_quality"

    # --- technical ---------------------------------------------------------
    APP_TECHNICAL = "app_technical"

    # --- everything else --------------------------------------------------
    OTHER = "other"

    # REMOVED, and the reason is the finding rather than the removal:
    # account_access and support_unresponsive do not exist as the SUBJECT of a
    # public review. Measured on the ticket-shaped pool - 1 account_access row
    # in the whole corpus, 2 support_unresponsive - because nobody writes a
    # store review to say they cannot log in; they write to support directly,
    # and that channel is not in this data. A category that cannot be measured
    # is dead weight in an evaluation. "Support was already contacted and did
    # not reply" survives as a FLAG on the label: it changes the tone and the
    # next step, never the subject.
    #
    # advisor_conduct went the same way on 2026-09-21, and the evidence is
    # stronger than for either of those two. It was kept for one reason - the
    # assignment names complaints about experts as one of its four themes - and
    # a category kept for a reason outside the data is exactly the thing this
    # comment block exists to catch. What the data says:
    #   - the probe fires on 0 of the 989 ticket-shaped rows in the whole
    #     43,941-row corpus, and on 0 of the 313 inside the freshness window;
    #   - a hand search for advisor-behaviour language - rude, never replied,
    #     not real, AI bot, next to psychic / advisor / astrologer - returned 11
    #     rows, and ALL ELEVEN are billing tickets that mention psychics in
    #     passing: a cancellation that does not work, a dollar that became
    #     forty-five, credits that were never added. Under "the primary cause is
    #     the one that has to be fixed for the charges to stop", not one of them
    #     is about an advisor;
    #   - it was never the primary label on any of the 182 labelled rows, and
    #     across 1,000 benchmark calls no model chose it as primary even once.
    # It survived only as a secondary tag: 2 labelled rows and 12 of 1,000 model
    # answers, always attached to "the psychics are fake AI" inside a billing
    # complaint. That is an accusation carried by a billing ticket, which is
    # what the FLAGS paragraph above already covers.
    #
    # MERGED on 2026-09-21: trial_converted, unauthorized_charge and
    # pricing_unclear became subscription_trap. They were three names for one
    # story - a subscription the writer did not knowingly agree to - separated
    # by whether the writer admitted to a first small payment, denied the charge
    # outright, or blamed the disclosure. Measured on golden2 across the three
    # leading models: F1 0.60 / 0.63 / 0.60 on unauthorized_charge, recall
    # 0.50 / 0.67 / 0.33 on pricing_unclear. Three of the fifteen consensus
    # flags sat on this boundary and so did three of the labels corrected by
    # hand the same day. The split earned nothing in routing either: all three
    # default to ask_purchase_rail, because refunds are routed by where the
    # purchase was made and none of the three says.
    #
    # data_privacy went on the same day, for the advisor_conduct reason: 4
    # usable rows in the whole 43,941-row corpus, and 3 of the 4 flagged by
    # model consensus, one of them 20 of 20 against us. A deletion request is
    # now `other` with escalate_to_human, which is what a statutory clock
    # actually needs.
    #
    # What does NOT go with it is the routing. A ticket genuinely about an
    # advisor's conduct still has to reach the separate Report a Safety Concern
    # intake (pol-08), and it still does: the category becomes `other` and the
    # action stays ROUTE_TO_SAFETY_REPORT. That pairing is not a guess - it is
    # how syn-01-crisis-explicit is already labelled, and v7 and v8 both pass
    # it. The routing lived in the next_step all along; the category was
    # duplicating it.


class Priority(str, Enum):
    """How soon a human must look.

    Set from facts stated in the text, never from tone and never from the star
    rating. Measured: the aggression lexicon fires on 37 of 100 golden rows
    while genuinely severe cases are a small fraction of that, so a
    tone-sensitive rule over-escalates and teaches agents to click past the
    banner.
    """

    P1 = "1"      # money still moving, legal exposure, or a vulnerable writer
    P2 = "2"      # money at stake but bounded, or paid-for service missing
    P3 = "3"      # quality, usability, questions, no money moving


class NextStep(str, Enum):
    """The ACTION to take, not the words to send.

    There is no "do nothing" step. Every ticket gets a reply, even praise and
    even a review that asks for nothing - the step for those is
    ACKNOWLEDGE_AND_CLOSE, which means a thank-you goes out and no further
    work is queued. A step called `no_action` would quietly authorise
    silence, and silence is the complaint in 22 tickets of the corpus.

    ASK_PURCHASE_RAIL is the modal value on purpose. Nebula routes refunds by
    where the subscription was bought - App Store purchases are refunded by
    Apple, Google Play and web purchases by Nebula support (policy pol-04) - and
    most billing tickets never say which. With ticket text as the only input
    neither a model nor a human agent can know it, so asking is the correct
    first action rather than a fallback.
    """

    ASK_PURCHASE_RAIL = "ask_purchase_rail"
    ROUTE_TO_APPLE = "route_to_apple"
    PROCESS_REFUND = "process_refund"
    GUIDE_CANCELLATION = "guide_cancellation"
    SEND_KB_ARTICLE = "send_kb_article"
    REQUEST_EVIDENCE = "request_evidence"
    # Nebula runs a separate Report a Safety Concern intake (pol-08). This is
    # the only step that leaves the support queue entirely, and it is reached
    # from `other` - advisor_conduct used to own it and no longer exists.
    ROUTE_TO_SAFETY_REPORT = "route_to_safety_report"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    ACKNOWLEDGE_AND_CLOSE = "acknowledge_and_close"


# --- definitions, each with a real quoted ticket -----------------------------
#
# The quote is the point. A rubric a human labeller cannot apply consistently is
# not a rubric, and the fastest way to make a boundary concrete is to show a row
# that sits on it. Every quote is verbatim PII-redacted corpus text, trimmed.
#
# Three keys, and only two of them reach the model:
#   definition  what the category is                    -> prompt
#   not         the boundary against its nearest neighbour -> prompt
#   note        our own reasoning about the taxonomy     -> NEVER rendered
CATEGORY_GUIDE: dict[Category, dict[str, str]] = {
    Category.REFUND_REQUEST: {
        "count": "167 of 313 in the window, 577 in the corpus",
        "definition": "Asks for money back. The charge itself is not disputed "
                      "as unauthorised - they want it reversed.",
        "example": "MI SONO RITROVATA CON 49 EURO IN MENO SUL CONTO ... ORA "
                   "CHIEDO IL RIMBORSO. COME FACCIO?",
        "not": "If the charge itself should not have happened, that is "
               "subscription_trap - the refund is then the demand, not the "
               "cause.",
        "note": "The single largest category, and the one whose next step "
                "depends on a fact the ticket usually omits: the store.",
    },
    Category.SUBSCRIPTION_TRAP: {
        "count": "141 of 313 in the window, 433 in the corpus (the three "
                 "merged probes, deduplicated)",
        "definition": "A subscription the writer did not knowingly agree to. "
                      "Covers all three ways it happens: a trial or a small "
                      "starting payment that silently became a recurring "
                      "charge, a charge the writer denies agreeing to at all, "
                      "and a price or term that was not visible before paying.",
        "example": "I thought I was downloading an app with 1.00 trial ... now "
                   "they are trying to take 45.00 from my account.",
        "not": "If the writer tried to stop it and could not, the mechanism is "
               "what is broken: cancellation_failed. If the charge is not in "
               "dispute and only the refund is stuck, that is refund_request.",
        "note": "The largest category by a distance, and formerly three: "
                "trial_converted, unauthorized_charge and pricing_unclear. "
                "Separating them asked the classifier to decide whether the "
                "writer admitted to the first payment, which is a question "
                "about the writer, not about the ticket - and it changed no "
                "routing, because all three end at ask_purchase_rail.",
    },
    Category.CANCELLATION_FAILED: {
        "count": "34 of 313 in the window, 114 in the corpus",
        "definition": "Cannot find or complete cancellation, or cancelled and "
                      "was billed anyway.",
        "example": "I have cancelled the subscription so many times and it "
                   "keeps charging me.",
        "not": "Wanting money back for a charge already taken is "
               "refund_request, and a charge that should never have happened "
               "is subscription_trap; this is about the MECHANISM not working.",
        "note": "Where the cancellation must happen depends on the store, same "
                "as refunds (pol-16).",
    },
    Category.SERVICE_NOT_DELIVERED: {
        "count": "7 of 313 in the window, 30 in the corpus",
        "definition": "Paid for a report, reading, sketch or credits that never "
                      "arrived or were never added to the balance.",
        "example": "Paid for my reading to be sent to my email. Said 10min ... "
                   "No reading.",
        "not": "Receiving something inaccurate is content_quality. This is "
               "receiving nothing.",
        "note": "The one billing-adjacent category the help centre does answer "
                "properly (hc: credits not topped up, reading not received).",
    },
    Category.CONTENT_QUALITY: {
        "count": "4 of 313 in the window, 16 in the corpus",
        "definition": "The reading, chart or sign is wrong, generic, or "
                      "contradicts other sources.",
        "example": "my love reading is incorrect and hasn't been fixed",
        "not": "If nothing arrived at all, that is service_not_delivered.",
        "note": "A reading that frightened or upset the writer still belongs "
                "here, with the distressing_content flag set as well. The "
                "standing policy answer is pol-11, entertainment purposes only.",
    },
    Category.APP_TECHNICAL: {
        "count": "2 of 313 in the window, 15 in the corpus",
        "definition": "The application misbehaves: crashes, will not load, "
                      "blank screens, wrong interface language.",
        "example": "I can't even type in my date of birth because it crashes "
                   "every 10 seconds",
        "not": "If the app works and only the billing fails, classify by the "
               "billing problem.",
        "note": "The assignment names bugs as one of four ticket types, yet "
                "they are 0.7% of the pool: nobody writes a public review to "
                "report a crash. Kept as a category for that reason, and the "
                "dataset reaches outside the freshness window to fill it.",
    },
    Category.OTHER: {
        "count": "93 of 313 rows match no probe",
        "definition": "A real ticket that fits none of the above. This is also "
                      "where a complaint about a specific advisor's conduct or "
                      "authenticity belongs, and where acute distress belongs: "
                      "neither has its own category, and both are carried by "
                      "the next_step route_to_safety_report. A request to "
                      "delete personal data or an account lands here too, with "
                      "escalate_to_human, because it carries a statutory clock "
                      "and no other category names it.",
        "example": "",
        "not": "",
        "note": "Not a dumping ground for low confidence - that is what the "
                "confidence field and the automation gate are for. The 34.1% "
                "is a probe-recall artefact, not a prediction: most of those "
                "rows are cancellation or trial stories phrased in words the "
                "probes do not carry.",
    },
}

PRIORITY_GUIDE: dict[Priority, str] = {
    Priority.P1: (
        "Money has been taken and the bleeding has not stopped, or there is "
        "legal exposure, or the writer shows a vulnerability marker. "
        "Concretely: a recurring charge the user cannot stop; a chargeback, "
        "lawyer or regulator named; a minor, a health disclosure or acute "
        "distress present."
    ),
    Priority.P2: (
        "Money is at stake but bounded, or something paid for was not "
        "delivered, or the user is locked out. One charge to reverse, a report "
        "that never arrived, an account that will not open."
    ),
    Priority.P3: (
        "No money is moving and nothing is blocked. Quality complaints, bugs, "
        "unclear pricing after the fact, questions, praise."
    ),
}


# Which next step is defensible for which category, before any per-ticket fact
# is considered. The classifier may choose outside this map; the evaluation
# reports when it does, because a defensible default is what makes a wrong
# routing visible rather than merely surprising.
DEFAULT_NEXT_STEP: dict[Category, NextStep] = {
    Category.SUBSCRIPTION_TRAP: NextStep.ASK_PURCHASE_RAIL,
    Category.CANCELLATION_FAILED: NextStep.GUIDE_CANCELLATION,
    Category.REFUND_REQUEST: NextStep.ASK_PURCHASE_RAIL,
    Category.SERVICE_NOT_DELIVERED: NextStep.REQUEST_EVIDENCE,
    Category.CONTENT_QUALITY: NextStep.SEND_KB_ARTICLE,
    Category.APP_TECHNICAL: NextStep.SEND_KB_ARTICLE,
    Category.OTHER: NextStep.ESCALATE_TO_HUMAN,
}


# --- the three boundaries that had to be decided by hand ---------------------
#
# Each of these came from a real disagreement while labelling the golden set.
# They are written here rather than left to judgement because an unwritten rule
# is applied differently by every reader, and the evaluation then measures the
# readers instead of the model.
LABELLING_RULES = [
    "Within the billing family the question is never HOW the charge arose. A "
    "trial that renewed, a charge the writer denies entirely, a price that was "
    "never shown: all three are subscription_trap. The question that decides "
    "the category is what has to be fixed. If the writer tried to stop it and "
    "could not, fix the mechanism: cancellation_failed. If only the refund is "
    "stuck, fix the refund: refund_request. Otherwise the charge itself should "
    "not have happened: subscription_trap.",

    "Priority 1 needs the aggravating fact to be STATED, not inferred. A "
    "charge that might recur, a subscription that is probably still live, a "
    "person who is probably upset - none of those raise the priority. "
    "Repetition, a named bank or lawyer, a deletion request or a disclosed "
    "vulnerability do, because they are in the text.",

    "A ticket the writer or support has ALREADY RESOLVED is priority 3 and "
    "acknowledge_and_close, however large the sum was. Money that has been "
    "refunded is not money at stake, and a reply is still owed - the writer "
    "took the trouble to report a pattern.",
]


def rules_for_prompt() -> str:
    return "\n".join(f"- {rule}" for rule in LABELLING_RULES)


def categories_for_prompt() -> str:
    """Render the taxonomy as the prompt sees it.

    Generated rather than duplicated as a string literal: a prompt that drifts
    from the enum produces confident labels outside the schema, and the only way
    to prevent it is to have one source. `note` and `count` are never rendered -
    they are our reasoning about the taxonomy, not instructions to a model.
    """
    lines = []
    for category, guide in CATEGORY_GUIDE.items():
        line = f"- {category.value}: {guide['definition']}"
        if guide.get("not"):
            line += f" NOT: {guide['not']}"
        lines.append(line)
    return "\n".join(lines)


def priorities_for_prompt() -> str:
    return "\n".join(f"- {p.value}: {text}" for p, text in PRIORITY_GUIDE.items())


def next_steps_for_prompt() -> str:
    return "\n".join(f"- {step.value}" for step in NextStep)


def examples_for_prompt() -> str:
    """One real quoted ticket per category, for the few-shot version of the
    prompt. Kept separate from categories_for_prompt() so the zero-shot
    baseline and the few-shot variant differ by exactly one block."""
    lines = []
    for category, guide in CATEGORY_GUIDE.items():
        if guide.get("example"):
            lines.append(f"- {category.value}: \"{guide['example']}\"")
    return "\n".join(lines)
