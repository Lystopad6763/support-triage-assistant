"""Assemble the three fragments into one HTML document and render it to PDF.

    python docs/build.py

The fragments are written separately (docs/_part1.html .. _part3.html) and this
script only frames them: a title page, a contents list generated from the h2/h3
headings actually present, print CSS, and Chrome in headless mode for the PDF.
Nothing here edits content, so re-running it after a fragment changes is safe and
the PDF never disagrees with its source.
"""
from __future__ import annotations

import html
import os
import re
import subprocess
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
PARTS = [DOCS / f"_part{n}.html" for n in (1, 2, 3)]
OUT_HTML = DOCS / "OBRIO_task1_documentation.html"
OUT_PDF = DOCS / "OBRIO_task1_documentation.pdf"

CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

CSS = """
@page { size: A4; margin: 17mm 15mm 16mm 15mm; }
* { box-sizing: border-box; }
body {
  font: 10.5pt/1.5 "Segoe UI", "Noto Sans", Arial, sans-serif;
  color: #1a1a1a; margin: 0;
}
h1 { font-size: 26pt; line-height: 1.15; margin: 0 0 6mm; font-weight: 650; }
h2 {
  font-size: 15pt; margin: 9mm 0 3mm; padding-bottom: 1.5mm;
  border-bottom: 1.4pt solid #1a1a1a; break-after: avoid; break-inside: avoid;
}
h3 {
  font-size: 11.5pt; margin: 6mm 0 2mm; color: #0f3d5c;
  break-after: avoid; break-inside: avoid;
}
p { margin: 0 0 2.6mm; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 3mm; padding-left: 6mm; }
li { margin-bottom: 1.4mm; }
code {
  font-family: "Cascadia Mono", Consolas, monospace; font-size: 9pt;
  background: #f1f3f5; padding: 0.3mm 1mm; border-radius: 1mm;
}
pre {
  background: #f7f8fa; border-left: 2.5pt solid #adb5bd; padding: 2.5mm 3mm;
  margin: 0 0 3mm; overflow-wrap: anywhere; white-space: pre-wrap;
  break-inside: avoid;
}
pre code { background: none; font-size: 8.4pt; line-height: 1.38; padding: 0; }
table {
  border-collapse: collapse; width: 100%; margin: 0 0 3.5mm; font-size: 9pt;
  break-inside: avoid;
}
th, td { border: 0.5pt solid #ced4da; padding: 1.3mm 1.8mm; text-align: left;
         vertical-align: top; }
th { background: #eef1f4; font-weight: 600; }
tbody tr:nth-child(even) { background: #fafbfc; }
strong { font-weight: 650; }
.title-page { height: 252mm; display: flex; flex-direction: column;
              justify-content: center; break-after: page; }
.subtitle { font-size: 13pt; color: #495057; margin-bottom: 14mm; }
.meta { font-size: 10pt; color: #495057; border-top: 0.5pt solid #ced4da;
        padding-top: 4mm; }
.meta div { margin-bottom: 1.6mm; }
.toc { break-after: page; }
.toc h2 { border-bottom: none; margin-top: 0; }
.toc ol { list-style: none; padding-left: 0; counter-reset: sec; }
.toc > ol > li { counter-increment: sec; margin-bottom: 1.6mm;
                 font-weight: 600; font-size: 10.5pt; }
.toc > ol > li::before { content: counter(sec) ". "; color: #0f3d5c; }
.toc ol ol { padding-left: 7mm; margin-top: 1mm; }
.toc ol ol li { font-weight: 400; font-size: 9.5pt; color: #495057;
                margin-bottom: 0.8mm; }
.part { break-before: page; }
.part-label { font-size: 9pt; letter-spacing: 0.12em; text-transform: uppercase;
              color: #0f3d5c; font-weight: 650; margin-bottom: 2mm; }
"""

PART_LABELS = {
    1: "Частина I. Система, дані, словник міток",
    2: "Частина II. Промпт, метрики, вимірювання",
    3: "Частина III. Межі, хроніка, додатки",
}

HEADING = re.compile(r"<(h2|h3)>(.*?)</\1>", re.S)
TAG = re.compile(r"<[^>]+>")


def headings(fragment: str) -> list[tuple[str, str]]:
    return [(level, TAG.sub("", text).strip())
            for level, text in HEADING.findall(fragment)]


def toc(fragments: dict[int, str]) -> str:
    lines = ['<div class="toc"><h2>Зміст</h2><ol>']
    for number, fragment in fragments.items():
        lines.append(f'<li>{html.escape(PART_LABELS[number])}<ol>')
        for level, text in headings(fragment):
            if level == "h2":
                lines.append(f"<li>{html.escape(text)}</li>")
        lines.append("</ol></li>")
    lines.append("</ol></div>")
    return "".join(lines)


def main() -> None:
    missing = [p.name for p in PARTS if not p.exists()]
    if missing:
        sys.exit(f"missing fragments: {missing}")
    fragments = {n: path.read_text(encoding="utf-8")
                 for n, path in zip((1, 2, 3), PARTS)}

    body = [
        '<div class="title-page">',
        "<h1>Автоматична класифікація тікетів підтримки</h1>",
        '<div class="subtitle">Тестове завдання OBRIO AI Ops, Task 1 — '
        "документація системи, методики вимірювання та прийнятих рішень</div>",
        '<div class="meta">',
        "<div><strong>Автор:</strong> Сергій Листопад</div>",
        "<div><strong>Продукт:</strong> Nebula (астрологія та консультації), "
        "тріаж звернень до підтримки</div>",
        "<div><strong>Дата:</strong> 21 вересня 2026</div>",
        "<div><strong>Дані:</strong> 43 941 реальний відгук App Store і Google "
        "Play, з них 100 розмічених тікетів у двох сетах і 15 синтетичних "
        "edge cases</div>",
        "<div><strong>Заморожений промпт:</strong> v8 — category 84% ± 3, "
        "macro F1 по класах із support ≥ 3: 0.79</div>",
        "</div></div>",
        toc(fragments),
    ]
    for number, fragment in fragments.items():
        body.append(f'<div class="part"><div class="part-label">'
                    f"{html.escape(PART_LABELS[number])}</div>")
        body.append(fragment)
        body.append("</div>")

    document = (
        "<!DOCTYPE html><html lang='uk'><head><meta charset='utf-8'>"
        "<title>OBRIO Task 1 — документація</title>"
        f"<style>{CSS}</style></head><body>{''.join(body)}</body></html>")
    OUT_HTML.write_text(document, encoding="utf-8")

    counts = {n: len(TAG.sub(" ", f).split()) for n, f in fragments.items()}
    print(f"words: " + "  ".join(f"part{n} {c:,}" for n, c in counts.items())
          + f"  total {sum(counts.values()):,}")

    chrome = next((c for c in CHROME if os.path.exists(c)), None)
    if not chrome:
        sys.exit("no Chrome or Edge found for rendering")
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri()],
        check=True, capture_output=True, timeout=180)
    print(f"wrote {OUT_PDF.relative_to(ROOT)} "
          f"({OUT_PDF.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
