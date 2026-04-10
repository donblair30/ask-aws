"""
Clean raw HTML into plain text by stripping navigation, headers, footers,
and other boilerplate that would pollute embeddings.

Usage:
    python -m ingest.clean              # clean all services
    python -m ingest.clean s3           # clean one service
    python -m ingest.clean path/to/file.html  # preview one file
"""

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

import config

# CSS selectors for boilerplate regions to remove before extracting text.
# Order matters: broader selectors first.
_STRIP_SELECTORS = [
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "[id='left-column']",
    "[id='right-column']",
    "[id='aws-nav']",
    "[id='awsdocs-page-header']",
    "[id='awsdocs-page-footer']",
    "[class*='breadcrumb']",
    "[class*='prev-next']",
    "[class*='feedback']",
    "[class*='cookie']",
    "[class*='awsnav']",
    "[class*='page-header']",
    "[class*='page-footer']",
]

# Candidate selectors for the main content region, tried in order.
_MAIN_SELECTORS = [
    "#main-content",
    "#awsdocs-container",
    "main",
    "article",
    "[class*='awsdocs-content']",
    "[role='main']",
]


def clean_html(html: bytes | str) -> str:
    """
    Parse HTML and return clean plain text containing only the main content.
    Returns an empty string if no content region is found.
    """
    soup = BeautifulSoup(html, "lxml")

    # Strip boilerplate elements in-place
    for selector in _STRIP_SELECTORS:
        for el in soup.select(selector):
            el.decompose()

    # Find the main content region
    main = None
    for selector in _MAIN_SELECTORS:
        main = soup.select_one(selector)
        if main:
            break
    if main is None:
        main = soup.body
    if main is None:
        return ""

    raw = main.get_text(separator="\n")

    # Normalise whitespace: strip each line, collapse blank runs to one blank line
    lines = [line.strip() for line in raw.splitlines()]
    cleaned: list[str] = []
    prev_blank = False
    for line in lines:
        if line:
            cleaned.append(line)
            prev_blank = False
        elif not prev_blank:
            cleaned.append("")
            prev_blank = True

    return "\n".join(cleaned).strip()


def clean_file(path: Path) -> str:
    """Clean a single cached HTML file and return plain text."""
    return clean_html(path.read_bytes())


def clean_service(service: str) -> None:
    """Clean all cached HTML files for a service; write .txt alongside each."""
    raw_dir = config.RAW_DIR / service
    if not raw_dir.exists():
        print(f"No raw data for {service}. Run fetch.py first.")
        return

    html_files = sorted(raw_dir.glob("*.html"))
    for i, html_path in enumerate(html_files, 1):
        txt_path = html_path.with_suffix(".txt")
        text = clean_file(html_path)
        txt_path.write_text(text, encoding="utf-8")
        print(f"[{i}/{len(html_files)}] cleaned {html_path.name}")

    print(f"\n{service}: {len(html_files)} files cleaned")


def clean_all() -> None:
    services = [d.name for d in config.RAW_DIR.iterdir() if d.is_dir()]
    for service in sorted(services):
        print(f"\n=== {service.upper()} ===")
        clean_service(service)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None

    if arg and Path(arg).exists():
        # Preview mode: print first 3000 chars of a single file
        print(clean_file(Path(arg))[:3000])
    elif arg:
        clean_service(arg.lower())
    else:
        clean_all()
