"""
Fetch raw HTML for each discovered URL and cache it to data/raw/{service}/.

Files are named by a hash of the URL so re-runs are idempotent — already-cached
pages are skipped unless --force is passed.

Usage:
    python -m ingest.fetch              # fetch all services
    python -m ingest.fetch s3           # fetch one service
    python -m ingest.fetch s3 --force   # re-fetch even if cached
"""

import hashlib
import sys
import time

import httpx

import config
from ingest.corpus import SERVICE_SITEMAPS, discover_urls


def url_to_filename(url: str) -> str:
    """
    Derive a stable filename from a URL.
    Uses the last path segment for readability plus an 8-char hash for uniqueness.
    """
    slug = url.rstrip("/").split("/")[-1] or "index"
    slug = slug.split("?")[0].split("#")[0]
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{slug}_{url_hash}.html"


def fetch_page(url: str, service: str, force: bool = False) -> bool:
    """
    Fetch one page and write to data/raw/{service}/{filename}.
    Returns True if a network request was made, False if served from cache.
    """
    service_dir = config.RAW_DIR / service
    service_dir.mkdir(parents=True, exist_ok=True)

    dest = service_dir / url_to_filename(url)
    if dest.exists() and not force:
        return False  # cache hit

    resp = httpx.get(
        url,
        headers=config.FETCH_HEADERS,
        follow_redirects=True,
        timeout=config.FETCH_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return True


def fetch_service(service: str, force: bool = False) -> None:
    """Fetch all pages for one service."""
    from ingest.corpus import discover_urls
    entries = discover_urls(service)
    total = len(entries)
    fetched = skipped = errors = 0

    for i, entry in enumerate(entries, 1):
        url = entry["url"]
        try:
            did_fetch = fetch_page(url, service, force=force)
            if did_fetch:
                fetched += 1
                print(f"[{i}/{total}] fetched  {url}")
                time.sleep(config.FETCH_DELAY_SECONDS)
            else:
                skipped += 1
                print(f"[{i}/{total}] cached   {url}")
        except Exception as exc:
            errors += 1
            print(f"[{i}/{total}] ERROR    {url}  —  {exc}")

    print(f"\n{service}: {fetched} fetched, {skipped} cached, {errors} errors")


def fetch_all(force: bool = False) -> None:
    for service in SERVICE_SITEMAPS:
        print(f"\n=== {service.upper()} ===")
        fetch_service(service, force=force)


if __name__ == "__main__":
    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]

    if args:
        fetch_service(args[0].lower(), force=force)
    else:
        fetch_all(force=force)
