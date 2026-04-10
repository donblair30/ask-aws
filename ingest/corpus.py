"""
Discover AWS documentation URLs via per-service sitemaps.

Each service sitemap is a standard XML sitemap at a predictable URL.
We filter out API reference pages, CLI reference pages, and release notes
since they produce low-quality RAG chunks.

Usage:
    python -m ingest.corpus              # print URL counts for all services
    python -m ingest.corpus s3           # print URLs for one service
"""

import re
import sys
import xml.etree.ElementTree as ET

import httpx

# Sitemap URL for each supported service's User Guide
SERVICE_SITEMAPS: dict[str, str] = {
    "s3":  "https://docs.aws.amazon.com/AmazonS3/latest/userguide/sitemap.xml",
    "ec2": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/sitemap.xml",
    "iam": "https://docs.aws.amazon.com/IAM/latest/UserGuide/sitemap.xml",
}

# URL substrings that indicate non-prose reference pages (poor RAG signal)
_EXCLUDE_PATTERNS: list[str] = [
    r"/API_",            # per-API-action pages  (e.g. API_PutObject.html)
    r"APIReference",     # API reference guides
    r"/api-reference",
    r"/cli/",            # AWS CLI reference
    r"cli-reference",
    r"_CLI_",
    r"/WhatsNew",        # What's new / changelog
    r"ReleaseNotes",
    r"/Release-Notes",
]

_EXCLUDE_RE = re.compile("|".join(_EXCLUDE_PATTERNS), re.IGNORECASE)

# Standard XML sitemap namespace
_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _fetch_sitemap(url: str) -> list[str]:
    """Download a sitemap XML and return all <loc> URLs."""
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    return [
        loc.text.strip()
        for loc in root.findall(".//sm:loc", _NS)
        if loc.text
    ]


def discover_urls(service: str) -> list[dict]:
    """
    Return a list of {"url": ..., "service": ...} dicts for a given service,
    filtered to exclude API/CLI reference pages.
    """
    service = service.lower()
    sitemap_url = SERVICE_SITEMAPS.get(service)
    if not sitemap_url:
        raise ValueError(
            f"Unknown service '{service}'. Supported: {sorted(SERVICE_SITEMAPS)}"
        )

    all_urls = _fetch_sitemap(sitemap_url)
    return [
        {"url": url, "service": service}
        for url in all_urls
        if not _EXCLUDE_RE.search(url)
    ]


def discover_all() -> list[dict]:
    """Return filtered URL entries for all configured services."""
    entries: list[dict] = []
    for service in SERVICE_SITEMAPS:
        service_entries = discover_urls(service)
        entries.extend(service_entries)
    return entries


if __name__ == "__main__":
    target = sys.argv[1].lower() if len(sys.argv) > 1 else None
    services = [target] if target else list(SERVICE_SITEMAPS)

    for svc in services:
        try:
            entries = discover_urls(svc)
            print(f"{svc}: {len(entries)} pages")
            if target:
                for e in entries[:10]:
                    print(f"  {e['url']}")
                if len(entries) > 10:
                    print(f"  ... and {len(entries) - 10} more")
        except Exception as exc:
            print(f"{svc}: ERROR — {exc}")
