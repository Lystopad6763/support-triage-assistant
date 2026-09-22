"""Re-run redaction over raw dumps already on disk.

WHY THIS EXISTS
    Redaction improves. When it does, the data collected under the old rules
    still carries what the new rules would have removed, and re-scraping 124
    App Store storefronts to fix it costs a rate-limit window for no new data.

    This pass is safe because the placeholders are idempotent: text that is
    already "[Name]" cannot match a pattern that requires a letter, so nothing
    is double-redacted. What it CANNOT do is recover from a redaction that fired
    too early — "[Name] Silva" stays that way, because the surname no longer has
    a first name in front of it for the pattern to see. Only a re-scrape fixes
    that class, which is why the self-test exists.

    Every run reports what changed and audits the result, so a pass that
    silently did nothing is visible as such.

Usage:
    python data/collect/scripts/reredact.py [--dry-run]
"""
from __future__ import annotations

import argparse
import glob
import json
import os

from common import (RAW_APPSTORE, RAW_GOOGLEPLAY, audit_pii, redact_reply,
                    redact_review, report_audit, self_test, write_json)

# store directory -> (review-body field, reply field)
SOURCES = {
    RAW_APPSTORE: ("text", "reply", "title"),
    RAW_GOOGLEPLAY: ("content", "reply", None),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change without writing")
    args = parser.parse_args()

    broken = self_test()
    if broken:
        print("!! REDACTION SELF-TEST FAILED, nothing was touched")
        for problem in broken:
            print(f"   {problem}")
        raise SystemExit(1)

    changed_files = changed_rows = 0
    fields: list[str] = []

    for directory, (body_key, reply_key, title_key) in SOURCES.items():
        for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
            document = json.load(open(path, encoding="utf-8"))
            touched = 0

            for row in document.get("reviews", []):
                before = (row.get(title_key) if title_key else None,
                          row.get(body_key), row.get(reply_key))
                if title_key and row.get(title_key):
                    row[title_key] = redact_review(row[title_key])
                if row.get(body_key):
                    row[body_key] = redact_review(row[body_key])
                if row.get(reply_key):
                    row[reply_key] = redact_reply(row[reply_key])
                after = (row.get(title_key) if title_key else None,
                         row.get(body_key), row.get(reply_key))
                if before != after:
                    touched += 1
                fields += [v for v in after if v]

            if touched:
                changed_files += 1
                changed_rows += touched
                print(f"  {os.path.basename(path):<16} {touched:4d} rows changed")
                if not args.dry_run:
                    write_json(document, path)

    verb = "would change" if args.dry_run else "changed"
    print(f"\n{changed_rows} rows {verb} across {changed_files} files")
    if args.dry_run:
        print("  (dry run — nothing written)")
    print("")
    report_audit(audit_pii(fields), len(fields))


if __name__ == "__main__":
    main()
