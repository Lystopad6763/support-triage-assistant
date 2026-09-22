"""Scrape Nebula's Zendesk help center — the knowledge base for Task 2.

Endpoint — Zendesk's public Help Center API, which needs no key:
    https://24hours.support-nebula.com/api/v2/help_center/{locale}/articles.json

The browsable /hc/ pages answer 403 to anything that is not a real browser, but
the API beside them is open. Worth knowing before concluding a help center is
unreachable.

WHY THIS MATTERS MORE THAN IT LOOKS
    The six categories are not a taxonomy someone invented for this project —
    they are the ones Nebula's own support organisation uses:

        About Nebula           7 articles
        Getting Started        4
        How to Use            13
        Account Management    13
        Subscriptions & Billing 3
        Tech Assistance       11

    A ticket classifier whose labels match the company's real categories can be
    checked against reality. One with invented labels can only be checked
    against itself.

    The article bodies are the company's own answers, so they serve twice: as
    the retrieval corpus Task 2 cites, and as the ground truth for what a
    correct next action is.

NOT REDACTED, DELIBERATELY
    These are company-authored articles, not user text, so there is no customer
    PII to remove — and running the greeting redaction over them would damage
    real content ("Hi there" opens several articles). They are audited instead:
    if a name ever does appear, the run says so rather than silently mangling
    the body.

Output: raw/helpcenter/{locale}.json

Usage:
    python scripts/collect/scrape_helpcenter.py [--locale en-us]
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import time

from common import COLLECT, audit_pii, http_get, report_audit, write_json

HELP_CENTER = "https://24hours.support-nebula.com/api/v2/help_center"
RAW_HELPCENTER = os.path.join(COLLECT, "raw", "helpcenter")

TAG = re.compile(r"<[^>]+>")
WHITESPACE = re.compile(r"[ \t]*\n[ \t]*")
BLANK_RUN = re.compile(r"\n{3,}")


def fetch_all(locale: str, resource: str) -> list[dict]:
    """Read every page of one Help Center collection."""
    url = f"{HELP_CENTER}/{locale}/{resource}.json?per_page=100"
    items: list[dict] = []
    while url:
        payload = json.loads(http_get(url, timeout=30))
        items += payload.get(resource, [])
        url = payload.get("next_page")
    return items


def to_text(body: str) -> str:
    """Flatten article HTML to plain text.

    Block tags become newlines rather than disappearing: these articles are
    mostly numbered steps, and running them together would destroy the one
    thing that makes an answer actionable.
    """
    text = re.sub(r"<(?:br|/p|/li|/h[1-6]|/div|/tr)[^>]*>", "\n", body or "")
    text = re.sub(r"<li[^>]*>", "• ", text)
    text = html.unescape(TAG.sub("", text))
    text = WHITESPACE.sub("\n", text)
    return BLANK_RUN.sub("\n\n", text).strip()


# Zendesk gives every heading in the editor a stable anchor id, and the article
# links to its own sections through them. They are the publisher's OWN section
# boundaries - 31 of the 51 articles carry 73 of them - which makes them better
# than any structure a regex could infer from the flattened text, and they are
# addressable: <article url>#h_01KTY8... opens the reader ON the section rather
# than at the top of a six-rail article.
HEADING = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.S | re.I)
ANCHOR = re.compile(r"\sid=\"(h_[^\"]+)\"", re.I)


def to_sections(body: str) -> list[dict]:
    """Split one article at every heading, keeping the path to it.

    The course rule is "1 chunk = 1 logical section (heading + content), cut by
    structure rather than by token count, keeping headings, lists and tables".
    These articles are three levels deep - 17 h2, 65 h3, 55 h4 across the 46
    indexed ones - so splitting only on h2 would leave "1.1 During login
    process" buried inside a chunk about something else.

    Each section carries its BREADCRUMB rather than its own heading alone:
    "How to reset password? > 1. AskNebula website > 1.1 During login process".
    A sub-heading on its own is unrecognisable both to a reader and to an
    encoder - that path is the "keep the headings" half of the rule.

    The anchor is the heading's own id when it has one and the nearest ancestor
    heading's otherwise, so every section stays addressable even where the
    editor gave the sub-heading no id. An anchor with no heading text is a
    second link target for the heading that follows, not a section: those are
    kept as aliases so a citation that used one still resolves.
    """
    marks = list(HEADING.finditer(body or ""))
    if not marks:
        return []

    out: list[dict] = []
    intro = to_text((body or "")[:marks[0].start()])
    if intro:
        out.append({"anchor": "", "aliases": [], "heading": "", "text": intro})

    path: dict[int, str] = {}
    anchors: dict[int, str] = {}
    pending: list[str] = []
    for index, mark in enumerate(marks):
        level = int(mark.group(1))
        found = ANCHOR.search(mark.group(0))
        anchor = found.group(1) if found else ""
        heading = to_text(mark.group(2))

        path = {k: v for k, v in path.items() if k < level}
        anchors = {k: v for k, v in anchors.items() if k < level}
        path[level] = heading
        if anchor:
            anchors[level] = anchor

        end = marks[index + 1].start() if index + 1 < len(marks) else len(body)
        text = to_text(body[mark.end():end])
        if not text:
            if anchor:
                pending.append(anchor)
            continue

        nearest = ""
        for depth in sorted(anchors, reverse=True):
            nearest = anchors[depth]
            break
        out.append({
            "anchor": nearest,
            "aliases": pending,
            "heading": " > ".join(path[k] for k in sorted(path) if path[k]),
            "text": text,
        })
        pending = []
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--locale", default="en-us",
                        help="help center locale (default: en-us). Support "
                             "writes its replies in English regardless of the "
                             "reviewer's language, so en-us is the one that "
                             "matches the reply corpus.")
    args = parser.parse_args()

    started = time.time()
    categories = {c["id"]: c for c in fetch_all(args.locale, "categories")}
    sections = {s["id"]: s for s in fetch_all(args.locale, "sections")}
    articles = fetch_all(args.locale, "articles")

    rows = []
    for article in articles:
        section = sections.get(article.get("section_id"), {})
        category = categories.get(section.get("category_id"), {})
        rows.append({
            "id": article.get("id"),
            "category": category.get("name"),
            "section": section.get("name"),
            "title": article.get("title"),
            "body": to_text(article.get("body")),
            "sections": to_sections(article.get("body")),
            # Kept so that a change of mind about structure costs a re-parse
            # rather than a re-scrape. The 2026-09-21 edit to "How to cancel
            # subscription?" changed only markup - the extracted text was
            # identical to the character - and without the source there is no
            # way to tell that apart from a real edit after the fact.
            "body_html": article.get("body") or "",
            "url": article.get("html_url"),
            "updated_at": article.get("updated_at"),
            "label_names": article.get("label_names") or [],
        })
    rows.sort(key=lambda r: (r["category"] or "", r["section"] or "", r["title"] or ""))

    os.makedirs(RAW_HELPCENTER, exist_ok=True)
    path = os.path.join(RAW_HELPCENTER, f"{args.locale}.json")
    write_json({
        "source": "zendesk_help_center",
        "host": "24hours.support-nebula.com",
        "locale": args.locale,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "counts": {"categories": len(categories), "sections": len(sections),
                   "articles": len(rows)},
        "categories": [
            {"name": c["name"],
             "articles": sum(1 for r in rows if r["category"] == c["name"])}
            for c in categories.values()
        ],
        "articles": rows,
    }, path)

    fields = [r[key] for r in rows for key in ("title", "body")]
    print(f"{len(rows)} articles in {len(categories)} categories "
          f"({time.time() - started:.0f}s) -> {path}")
    for category in categories.values():
        inside = [r for r in rows if r["category"] == category["name"]]
        chars = sum(len(r["body"]) for r in inside)
        print(f"  {category['name']:<24} {len(inside):3d} articles, "
              f"{chars:6,d} chars")
    print("")
    # Audited, never redacted — see the note at the top of this file.
    report_audit(audit_pii(fields), len(fields))


if __name__ == "__main__":
    main()
