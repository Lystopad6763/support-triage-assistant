"""The knowledge base: 84 documents from three sources, loaded as one type.

The three files disagree about shape, and the disagreement is not cosmetic.
Help-centre articles carry a numeric Zendesk id, a category, a section and an
updated_at; the FAQ carries none of those and its id is already a string; the
policies carry a verified url and an operational_note. A retriever that had to
know which source a document came from in order to read its title would leak
that knowledge into every caller, so the shapes are reconciled once, here.

WHAT DELIBERATELY DOES NOT REACH THE MODEL
    operational_note   our own notes about how a policy is used in triage
                       ("the company's own do-not-automate list"). It is
                       methodology, not knowledge. Prompt v1 of the classifier
                       shipped with exactly this kind of note leaked into the
                       rendered text, naming a field the model did not have.
    retired_articles   pol-07, kept in the raw file with its reason and excluded
                       here: no page could be found for it, so it cannot be
                       cited, and a citation that cannot be opened is worse than
                       no citation at all.

IDS ARE THE ONES ALREADY IN USE
    hc-<zendesk id>, faq-NN, pol-NN - the strings ANSWERS below maps categories
    onto, and the ones every citation names. Renaming them here would silently
    unhook that table, so verify() asserts every id it names still exists.
"""
from __future__ import annotations

import difflib
import json
import re
from collections import Counter
from dataclasses import dataclass, asdict, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "collect" / "raw"

SOURCES = {
    "hc": (RAW / "helpcenter" / "en-us.json", "hc-{}"),
    "faq": (RAW / "faq" / "asknebula.json", "{}"),
    "pol": (RAW / "policies" / "asknebula_policies.json", "{}"),
}

# A rough token count, used for sizing decisions and never for billing: the real
# count comes back from the provider in usage. Four characters per token is the
# English approximation and it is wrong for the non-Latin queries, which is
# exactly why it is not allowed anywhere near a cost figure.
CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class Doc:
    """One knowledge-base document, whatever file it came from."""

    id: str
    source: str            # hc | faq | pol
    title: str
    body: str
    category: str
    section: str = ""      # help centre only
    url: str = ""
    # Whether the url opens THIS document or the page that contains it. The FAQ
    # is a client-rendered React page with no per-question anchor, so its 14
    # documents share one url and land the reader on all fourteen. A citation
    # that says "here" when it means "somewhere on this page" wastes the
    # agent's time silently, so the distinction travels with the document.
    url_is_page: bool = False
    url_status: str = ""   # policies only
    updated_at: str = ""   # help centre only
    # The publisher's own section anchors, as collected. Help centre only: the
    # FAQ page has none and a policy is one statement. Empty for everything
    # else, which is what makes split_sections fall back to the whole document.
    sections: tuple[dict, ...] = ()

    @property
    def text(self) -> str:
        """What gets embedded, and what gets shown to the model.

        The title is part of it on purpose. Half of these documents are phrased
        as the question a user asks ("How to cancel subscription?"), so the
        title is often a closer match to a ticket than any sentence in the body.
        """
        return f"{self.title}\n\n{self.body}"

    @property
    def tokens_est(self) -> int:
        return round(len(self.text) / CHARS_PER_TOKEN)


# --- what is collected but not searchable ------------------------------------
#
# Judged against the 384 hand-picked tickets, not against intuition: their
# themes are refund 66%, subscription or charge 66%, cancellation 43%, trial
# 20%, advisor quality 18%, technical 13%. Every document below was checked by
# reading the tickets that mention its words, because a word match is not a
# need - "discount" appears in five tickets and all five are complaints about
# being charged, not questions about discounts.
#
# They stay in data/collect/raw: the collection is evidence of what was
# gathered, and a decision that can be reversed by deleting one line here is
# worth more than one that needs a re-scrape. They are simply never indexed, so
# they cannot be retrieved and cannot be cited.
EXCLUDED: dict[str, str] = {
    "hc-28871801954321": "marketing: what Nebula is. 0 of 384 tickets ask",
    "hc-28871622557841": "marketing: users' experience. 0 tickets ask",
    "hc-28871823758865": "marketing: core values and mission. 0 tickets ask",
    "hc-28871657982865": "marketing: where to read more about Nebula. 0 tickets",
    "hc-28870571060497": "recruiting: how to work AS a psychic. 0 tickets",
    "faq-01": "pre-sale: what a consultation can bring. 0 tickets ask",
    "faq-02": "pre-sale: how the platform improves daily life. 0 tickets",
    "faq-04": "pre-sale: how to prepare for a reading. 0 tickets ask",
    "faq-05": "pre-sale: how to get a faster, more precise reading. 0 tickets",
    "faq-07": "pre-sale: how reviews are displayed. 0 tickets ask",
    # Not about need - about a claim. It states that every psychic passes
    # security and reputation checks, and pol-11, quoted from the verified
    # Terms, states that the company does NOT warrant that any advisor is
    # licensed or qualified. The same unsourced claim already cost pol-07 its
    # place during collection. Two documents in one index answering the same
    # question in opposite directions means the assistant can cite either one,
    # so the one without a source goes.
    "faq-06": "contradicts pol-11 (Terms) on advisor screening, unsourced",
}


# --- which documents could answer a ticket of which kind ----------------------
#
# Keyed by the taxonomy the 417 tickets are actually labelled with. The
# previous table, scripts/criteria.py:KB_ANSWERS, is keyed by a taxonomy that
# no longer exists - refund_request, subscription_trap, content_quality - and
# is left there only because the paused selection code still reads it.
#
# This is NOT a gold set. It is the shortlist that makes setting a gold fast,
# and it is deliberately generous: "could answer", not "does answer". Which
# document actually answers a given ticket is a per-ticket judgement.
#
# The mapping from the old keys was mechanical:
#     refund_request + unauthorized_charge          -> charge_not_recognised
#     subscription_trap/trial_converted/pricing_unclear -> price_not_expected
#     cancellation_failed                           -> cancel_not_possible
#     service_not_delivered                         -> nothing_delivered
#     app_technical                                 -> app_defect
#     advisor_conduct + data_privacy                -> other
#     content_quality                               -> gone as a category; its
#         documents live under `other`, because a complaint about a reading now
#         lands wherever its demand does.
ANSWERS: dict[str, list[str]] = {
    "charge_not_recognised": [
        "pol-13",              # the small verification charge, back in 10 days
        "pol-04",              # who decides the refund - Apple or us
        "pol-14",              # a confirmed refund takes 15 business days
        "pol-18",              # withdrawal rights, 14 days EEA/UK, 7 Brazil
        "pol-05",              # balance units, per-minute charging, auto-refill
        "pol-16",              # where to cancel, by rail
        "hc-28900802305297",   # how to cancel
    ],
    "price_not_expected": [
        "faq-09",              # how the payment system works
        "hc-28898955150609",   # how much it costs to chat
        "pol-05",
        "hc-28898312929809",   # my credits run out very fast
        "hc-36833668975505",   # why is the message blurred
        "pol-18",              # the withdrawal clock starts at the free trial
    ],
    "cancel_not_possible": [
        "hc-28900802305297",
        "pol-16",
        "hc-28899709030417",   # web subscription not visible on the phone
        "hc-28899740398481",   # store subscription not visible on the website
        "pol-04",
    ],
    "nothing_delivered": [
        "hc-28900034911377",   # how to access my report or reading
        "hc-28901216899857",   # paid for credits, balance not topped up
        "hc-28901045413393",   # reading ordered on social networks
        "faq-14",              # compatibility report: up to an hour, check spam
        "hc-28899179430801",   # no answer from the psychic
        "pol-19",              # advisor availability and how long a chat runs
    ],
    "app_defect": [
        "hc-28901074285713",   # Nebula is not working correctly
        "hc-28901224006801",   # error when logging in
        "hc-28901395830673",   # how to update the app
        "hc-28900840466961",   # I can not open my reading
        "hc-28901285302673",   # tech issues during a chat
        "hc-36800803666577",   # I cannot send my question in chat
    ],
    "other": [
        "pol-08",              # reporting a safety concern is a separate intake
        "pol-20",              # readings are human-led
        "pol-09",              # no fear-based messaging
        "pol-11",              # entertainment only, no warranty of qualification
        "hc-28900868231441",   # my report or reading is wrong
        "faq-13",              # how the zodiac sign was calculated
        "hc-28899811054737",   # remove personal data or delete the account
    ],
}


def load() -> list[Doc]:
    docs: list[Doc] = []
    for source, (path, shape) in SOURCES.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        # The FAQ records its address once, for the page, because that is the
        # only address it has. Reading it from the file rather than hard-coding
        # it here keeps one source of truth for where a document came from.
        page_url = payload.get("url", "")
        for article in payload["articles"]:
            url = article.get("url", "")
            docs.append(Doc(
                id=shape.format(article["id"]),
                source=source,
                title=article["title"].strip(),
                body=article["body"].strip(),
                category=article.get("category", ""),
                section=article.get("section", ""),
                url=url or page_url,
                url_is_page=not url and bool(page_url),
                url_status=article.get("url_status", ""),
                updated_at=article.get("updated_at", ""),
                sections=tuple(article.get("sections") or ()),
            ))
    return page_urls(docs)


def page_urls(docs: list[Doc]) -> list[Doc]:
    """Mark every address that several documents share as a page address.

    url_is_page was decided per document - "this one had no url of its own, so
    it inherited the page's" - which is right for the FAQ and wrong for the
    policies. Ten of them carry their own url and it is the same /terms page,
    so the flag said "this link opens this document" about a page holding ten.

    Whether an address is a page is a fact about the corpus, not about one
    record, so it is settled here, once everything is loaded. An agent who
    clicks a citation marked as a page knows to look for the passage; one who
    clicks a citation marked otherwise expects to land on it.
    """
    shared = Counter(d.url for d in docs if d.url)
    return [replace(doc, url_is_page=True)
            if shared[doc.url] > 1 and not doc.url_is_page else doc
            for doc in docs]


def indexed(docs: list[Doc] | None = None) -> list[Doc]:
    """What the retriever sees: everything collected, minus EXCLUDED."""
    docs = docs if docs is not None else load()
    return [d for d in docs if d.id not in EXCLUDED]


def crisis_resources() -> dict:
    """Country-keyed hotlines, and the reason they are keyed that way.

    Not a document and never retrieved: this is what the safety pre-pass reads
    when a ticket names self-harm, and the lookup is by country because the
    company's own page is. "worldwide" is the fallback, and it is what every
    Google Play ticket gets - there the locale is a language, not a country.
    """
    payload = json.loads(SOURCES["pol"][0].read_text(encoding="utf-8"))
    return payload["crisis_resources"]


# --- the section variant, built to be measured against article-as-chunk ------
#
# The boundaries are not inferred. Zendesk gives every heading in the editor a
# stable anchor id and the article links to its own sections through them, so
# the collector keeps them: 167 sections across 47 of the 51 help-centre
# articles. A regex over the flattened text found structure in 8 articles,
# which is the difference between reading the publisher's markup and guessing
# at it. The anchors are also addressable, so a section cites as
# <article url>#h_01KTY8... and opens the reader ON the rail rather than at the
# top of a six-rail article.
#
# Below this a section is merged into its neighbour rather than kept. A 12-token
# chunk retrieves on noise and carries no answer, but dropping it would make its
# content unreachable in this variant, so it is merged and not discarded.
MIN_SECTION_TOKENS = 40


@dataclass(frozen=True)
class Section:
    """A child of a Doc. The citation still names the parent."""

    id: str                # <doc id>#<n>
    doc_id: str
    source: str
    title: str             # the parent's title, kept for context enrichment
    heading: str
    body: str
    category: str
    url: str               # already carries #anchor when the section has one
    anchor: str = ""

    @property
    def text(self) -> str:
        if self.heading:
            return f"{self.title} - {self.heading}\n\n{self.body}"
        return f"{self.title}\n\n{self.body}"

    @property
    def tokens_est(self) -> int:
        return round(len(self.text) / CHARS_PER_TOKEN)


def _leaf(heading: str) -> str:
    """The last step of a breadcrumb, which is the heading itself."""
    return heading.split(" > ")[-1].strip()


def is_navigation(text: str, headings: set[str]) -> bool:
    """A table of contents, which is the article's own headings listed twice.

    The cancellation article opens with the six rail names as links. As a chunk
    it is a magnet: it names every topic in the article and answers none of
    them. It is recognised rather than guessed at - most of its lines ARE the
    headings that follow.
    """
    lines = [line.strip(" .") for line in text.split("\n") if line.strip()]
    if not lines:
        return True
    matched = sum(1 for line in lines
                  if any(line.lower().lstrip("0123456789. ") in head
                         for head in headings))
    return matched / len(lines) >= 0.6


def split_sections(doc: Doc) -> list[Section]:
    """Sections of one document, or one section holding the whole of it."""
    whole = [Section(id=f"{doc.id}#0", doc_id=doc.id, source=doc.source,
                     title=doc.title, heading="", body=doc.body,
                     category=doc.category, url=doc.url)]
    if not doc.sections:
        return whole

    headings = {_leaf(s["heading"]).lower().lstrip("0123456789. ")
                for s in doc.sections if s.get("heading")}

    kept: list[dict] = []
    for section in doc.sections:
        text = section.get("text", "").strip()
        if not text or is_navigation(text, headings):
            continue
        size = round(len(text) / CHARS_PER_TOKEN)
        # Merged into the previous section rather than dropped: unreachable
        # content is a worse failure than a slightly long chunk, and the parent
        # article is what gets cited either way.
        if size < MIN_SECTION_TOKENS and kept:
            kept[-1]["text"] += "\n\n" + (section.get("heading") or "")
            kept[-1]["text"] = kept[-1]["text"].strip() + "\n" + text
            continue
        kept.append({"anchor": section.get("anchor", ""),
                     "heading": section.get("heading", ""), "text": text})

    if not kept:
        return whole

    out: list[Section] = []
    for index, section in enumerate(kept):
        anchor = section["anchor"]
        out.append(Section(
            id=f"{doc.id}#{index}", doc_id=doc.id, source=doc.source,
            title=doc.title, heading=section["heading"], body=section["text"],
            category=doc.category, anchor=anchor,
            url=f"{doc.url}#{anchor}" if anchor and doc.url else doc.url))
    return out


# --- one copy of the boilerplate, not forty ----------------------------------
#
# "Contact our support team, and we will be happy to assist you" closes 40 of
# the 167 sections in this help centre - a quarter of the index, 2,000 tokens,
# twelve of them identical to the character. As chunks they crowd the top-5 out
# of every query without answering any of them.
#
# They are collapsed to one canonical copy rather than deleted, because that
# copy carries the one thing a drafter needs from it: which details to ask the
# customer for (a screenshot of the payment, the last four digits and the BIN,
# country of residence, the email used to register).
#
# The threshold is the course's own: SHA-256 for the exact matches, then
# SequenceMatcher at 0.7 for the rest.
DUPLICATE_RATIO = 0.7
# ...with one guard the course does not name, and which a measurement demanded.
# Blind dedup at 0.7 would have removed "I can not open my reading", a 0.93
# match to "How to access my report or reading" - and with it the line "check
# your Spam, Promotions, or Junk folders", which is the answer to the 43
# tickets that say the reading never arrived. A near-duplicate that carries
# sentences of its own is not a duplicate.
MIN_UNIQUE_SENTENCES = 2


def _normalise(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n", text)
    return [re.sub(r"\s+", " ", part).strip() for part in parts
            if len(part.strip()) > 25]


def sections(docs: list[Doc] | None = None) -> list[Section]:
    """Every section of every indexed document, boilerplate collapsed.

    Deduplication is a property of the corpus, not of one document, so it
    happens here and not in split_sections. Order decides which copy is the
    canonical one, and the order is the collector's - category, then section,
    then title - so it is stable across rebuilds.
    """
    docs = docs if docs is not None else indexed()

    kept: list[Section] = []
    orphans: dict[str, Section] = {}
    for doc in docs:
        alive = False
        biggest: Section | None = None
        for section in split_sections(doc):
            if biggest is None or section.tokens_est > biggest.tokens_est:
                biggest = section
            body = _normalise(section.body)
            twin = next((k for k in kept
                         if difflib.SequenceMatcher(
                             None, body, _normalise(k.body)).ratio()
                         >= DUPLICATE_RATIO), None)
            if twin is None:
                kept.append(section)
                alive = True
                continue
            pool = " ".join(_sentences(twin.body)).lower()
            unique = [s for s in _sentences(section.body)
                      if s.lower() not in pool]
            if len(unique) >= MIN_UNIQUE_SENTENCES:
                kept.append(section)
                alive = True
        # Comparison is on the BODY, because that is where the boilerplate
        # repeats; the vector is built from title + breadcrumb + body, where it
        # does not. That gap once removed an entire document: every section of
        # "Where is my reading ordered on Social networks (Facebook,
        # Instagram)?" is a near-copy of "How to access my report or reading",
        # so the article vanished from this variant while the coverage table
        # still named it the answer to service_not_delivered - and its title is
        # the only place the social-media purchase rail is named.
        # A document that is indexed must be retrievable, so its largest
        # section survives deduplication even when its body says nothing new.
        if not alive and biggest is not None:
            orphans[doc.id] = biggest

    kept.extend(orphans.values())
    return kept


def verify(docs: list[Doc] | None = None) -> list[Doc]:
    """Fail loudly on the four things that would otherwise break quietly."""
    docs = docs if docs is not None else load()

    ids = [d.id for d in docs]
    if len(set(ids)) != len(ids):
        raise SystemExit("duplicate knowledge-base ids")
    if len(docs) != 84:
        raise SystemExit(f"expected 84 documents, loaded {len(docs)}")

    # ANSWERS lives here rather than in scripts/, so the knowledge base does not
    # depend on the ticket-selection code. It did once, and when scripts/ was
    # briefly gone from the working tree, kb.verify() failed with an import
    # error that said nothing about the real cause.
    cited = {a for articles in ANSWERS.values() for a in articles}
    missing = sorted(cited - set(ids))
    if missing:
        raise SystemExit("ANSWERS cites documents that do not load: "
                         + ", ".join(missing))

    # Excluding a document that the coverage table names as the answer to a
    # category would make that category answerable on paper and unanswerable in
    # fact.
    muted = sorted(cited & set(EXCLUDED))
    if muted:
        raise SystemExit("EXCLUDED removes documents ANSWERS relies on: "
                         + ", ".join(muted))
    unknown = sorted(set(EXCLUDED) - set(ids))
    if unknown:
        raise SystemExit("EXCLUDED names documents that do not exist: "
                         + ", ".join(unknown))

    # A citation the agent cannot open is not a citation. All 84 documents have
    # an address today - 51 Zendesk articles, 19 verified policy pages and the
    # FAQ page shared by 14 - so the day one of them loses it is the day this
    # fires, rather than the day an agent is handed a quote with nowhere to go.
    unaddressed = [d.id for d in docs if not d.url]
    if unaddressed:
        raise SystemExit("documents with no url, so nothing to cite: "
                         + ", ".join(unaddressed))

    # The encoders in use accept 8191 tokens (OpenAI) and 8192 (bge-m3), and
    # silently drop the rest. The longest document here is 861, so this can only
    # fire if the knowledge base is re-collected with something much larger -
    # which is exactly when nobody would be watching for it.
    oversize = [d.id for d in docs if d.tokens_est > 8000]
    if oversize:
        raise SystemExit("longer than the encoder window, would be truncated "
                         "silently: " + ", ".join(oversize))
    return docs


def as_dict(doc: Doc) -> dict:
    payload = asdict(doc)
    payload["tokens_est"] = doc.tokens_est
    return payload
