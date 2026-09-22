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
    python data/collect/scripts/scrape_helpcenter.py [--locale en-us]
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
