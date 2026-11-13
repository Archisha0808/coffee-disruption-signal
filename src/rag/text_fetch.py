"""
Article-text fetch with parallel execution.

GDELT DOC 2.0 gives title/url/date/metadata only, no body text. This module
fetches each article's URL directly and extracts readable body text with
trafilatura (handles boilerplate/nav/ad stripping far better than naive
HTML tag removal).

Parallelism: articles come from many different domains, so concurrent
fetching doesn't hammer any single server. A ThreadPoolExecutor with 5
workers cuts a 20-article batch from ~25s (sequential + politeness delay)
to ~5s. Per-domain rate limiting is enforced: if two articles share a
domain, the second waits 1s after the first finishes.

Scoped intentionally: no JS rendering, no paywall/login bypass, no
pagination handling. A site that needs any of that counts as a failed
fetch. A failed or empty fetch returns "" (never fabricated text) - callers
fall back to title-only scoring for that document, and failure counts are
tracked so the overall fetch success rate is a reportable statistic.
"""

import hashlib
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
import trafilatura

try:
    import htmldate                     # installed with trafilatura
except ImportError:                     # pragma: no cover - optional
    htmldate = None

FETCH_TIMEOUT_SECONDS = 20  # arbitrary news sites, not GDELT's own slow API
CONNECT_TIMEOUT_SECONDS = 6  # a host that has not answered a connect in this
                             # long is down; waiting the full read timeout for
                             # it (twice, with retries) is most of what made a
                             # run slow
MAX_ATTEMPTS = 2
BACKOFF_SECONDS = 3
MAX_WORKERS = 5  # concurrent fetches (different domains, so this is polite)
SAME_DOMAIN_DELAY_SECONDS = 1.0  # rate limit per domain to avoid hammering

# ---------------------------------------------------------------------------
# Text-fetch cache: successful extractions are cached on disk so the same URL
# is never re-fetched. ~50% of article URLs are dead (404, 403, DNS failure,
# paywall) and each dead URL costs up to 20s of timeout. Caching the successes
# means a second pipeline run for the same date finishes in seconds, and the
# success rate is locked in even if the site goes down later.
# Failures are NOT cached — a URL that was down today might be up tomorrow.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEXT_CACHE_DIR = REPO_ROOT / "data" / "text_cache"


def _text_cache_key(url: str) -> str:
    """Stable hash of a URL for the text-fetch cache filename."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


def page_date(html: str, url: str = None) -> Optional[str]:
    """The publication date the page states about itself (YYYY-MM-DD), or None.

    Why: the listed date of a document comes from the search (GDELT's
    crawl time, or the pubDate Google News puts in its feed), not from the
    article. An article dated 3 September by the article itself has appeared
    as current news, so a listed date can be wrong; if it is earlier than the
    real one, an article written after the move could pass the "nothing after
    the anomaly date" filter. original_date=True asks for the first-published
    date, not the last-modified one."""
    if not html or htmldate is None:
        return None
    try:
        found = htmldate.find_date(html, original_date=True, extensive_search=False,
                                   outputformat="%Y-%m-%d", url=url)
    except Exception:  # noqa: BLE001 - a page that will not parse has no date
        return None
    # A page with no date of its own can come back dated today (the audit of
    # the version 11 runs found an Arabic page dated the day it was fetched,
    # for a 2021 move). Today is never a real publication date for a past
    # move, so it counts as no date.
    from datetime import datetime, timezone
    if found and found >= datetime.now(timezone.utc).strftime("%Y-%m-%d"):
        return None
    return found


def cached_article_date(url: str) -> Optional[str]:
    """The page's own date as recorded when its text was fetched, or None
    (not fetched, fetched before dates were recorded, or no date found)."""
    path = TEXT_CACHE_DIR / f"{_text_cache_key(url)}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("own_date")
    except (ValueError, OSError):
        return None


def _text_cache_get(url: str) -> Optional[str]:
    """Return cached extracted text for this URL, or None on miss."""
    path = TEXT_CACHE_DIR / f"{_text_cache_key(url)}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            entry = json.load(f)
        return entry.get("text", "")
    except (ValueError, OSError):
        return None


def cached_article_text(url: str) -> Optional[str]:
    """Body text for this URL if it is already in the on-disk cache, else
    None. Never touches the network - for offline evaluation runs that must
    see exactly the text an earlier live run extracted."""
    return _text_cache_get(url)


def _text_cache_put(url: str, text: str, own_date: Optional[str] = None) -> None:
    """Cache a successful text extraction. Best-effort — never crashes."""
    try:
        TEXT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = TEXT_CACHE_DIR / f"{_text_cache_key(url)}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"url": url, "text": text, "own_date": own_date}, f)
    except OSError:
        pass


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}

# Per-domain last-fetch timestamp to enforce politeness when multiple
# articles share the same domain. Thread-safe via lock.
_domain_locks = {}
_domain_lock_mutex = threading.Lock()


def _get_domain(url: str) -> str:
    """Extract the domain from a URL for rate limiting."""
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _wait_for_domain(domain: str):
    """Enforce per-domain rate limiting. If we fetched from this domain
    recently, sleep until the cooldown has passed."""
    if not domain:
        return

    with _domain_lock_mutex:
        if domain not in _domain_locks:
            _domain_locks[domain] = {"lock": threading.Lock(), "last_fetch": 0.0}
        info = _domain_locks[domain]

    with info["lock"]:
        elapsed = time.monotonic() - info["last_fetch"]
        if elapsed < SAME_DOMAIN_DELAY_SECONDS:
            time.sleep(SAME_DOMAIN_DELAY_SECONDS - elapsed)
        info["last_fetch"] = time.monotonic()


def fetch_article_text(url: str, verbose: bool = False) -> tuple[str, Optional[str]]:
    """
    Fetch and extract body text for one article URL.

    Returns (text, error). `text` is "" on any failure (never fabricated).
    `error` is None on success, or a short reason string on failure - kept
    separate from the text field itself so failures are visible in logs/
    stats rather than indistinguishable from "article had no text".

    Successful extractions are cached on disk (data/text_cache/) so the same
    URL is never re-fetched. Failures are not cached — a URL that was down
    today might be up tomorrow.
    """
    # Check the disk cache first — avoids the network entirely for known URLs
    cached = _text_cache_get(url)
    if cached is not None:
        return cached, None

    domain = _get_domain(url)
    _wait_for_domain(domain)

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.get(
                url, headers=HEADERS,
                timeout=(CONNECT_TIMEOUT_SECONDS, FETCH_TIMEOUT_SECONDS)
            )
            resp.raise_for_status()
            extracted = trafilatura.extract(resp.text, include_comments=False)
            if extracted and extracted.strip():
                text = extracted.strip()
                _text_cache_put(url, text, page_date(resp.text, url))  # cache the success
                return text, None
            last_error = "fetched OK but no extractable body text (paywall/JS/empty page?)"
            break  # a successful-but-empty fetch is not worth retrying
        except requests.exceptions.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < MAX_ATTEMPTS:
                if verbose:
                    print(f"    text fetch failed (attempt {attempt}), retrying: {last_error}")
                time.sleep(BACKOFF_SECONDS)

    if verbose:
        print(f"    text fetch failed for {url}: {last_error}")
    return "", last_error


def _fetch_one(index: int, doc: dict, total: int, verbose: bool) -> tuple[int, str, str]:
    """Fetch text for a single document. Returns (index, text, error)."""
    url = doc.get("url", "")
    if not url:
        return index, "", "no URL"
    if verbose:
        print(f"  [{index+1}/{total}] fetching text: {url[:80]}")
    text, error = fetch_article_text(url, verbose=verbose)
    return index, text, error or ""


def fetch_texts_for_documents(documents: list[dict], verbose: bool = True,
                              max_workers: int = MAX_WORKERS) -> dict:
    """
    Fetch body text for a list of documents in parallel. Each document needs
    a 'url' key. Returns stats: {"attempted": n, "succeeded": n, "failed": n}.
    Mutates each document dict in place, setting 'text' and 'text_fetch_error'.

    Uses a thread pool with per-domain rate limiting: articles from different
    domains run concurrently, but two articles from the same domain are
    separated by a 1-second delay. This is polite to individual servers
    while being 4-5x faster overall than fully sequential fetching.
    """
    stats = {"attempted": 0, "succeeded": 0, "failed": 0}
    total = len(documents)

    if total == 0:
        return stats

    # For very small batches, sequential is fine
    if total <= 2:
        max_workers = 1

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_one, i, doc, total, verbose): i
            for i, doc in enumerate(documents)
        }

        for future in as_completed(futures):
            idx = futures[future]
            stats["attempted"] += 1
            try:
                _, text, error = future.result()
                documents[idx]["text"] = text
                documents[idx]["text_fetch_error"] = error
                if text:
                    stats["succeeded"] += 1
                else:
                    stats["failed"] += 1
            except Exception as exc:
                documents[idx]["text"] = ""
                documents[idx]["text_fetch_error"] = f"thread error: {exc}"
                stats["failed"] += 1

    if verbose:
        print(f"  Text fetch complete: {stats['succeeded']}/{stats['attempted']} succeeded "
              f"({max_workers} workers)")

    return stats
