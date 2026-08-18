"""Resolves and caches movie poster image URLs via TMDb.

Requires a free TMDb API key (https://www.themoviedb.org/settings/api)
set as the TMDB_API_KEY environment variable. One lookup by IMDb ID
returns the poster path directly -- no scraping involved.

The browser only fetches the actual image bytes later, on hover, via the
URL we hand it -- resolving the URL here never loads image data itself.

Live app renders only ever read the local cache (fast, no network) via
get_poster_urls(). Run `python warm_poster_cache.py` (once, or on a cron)
to actually populate it -- that's the only place network calls happen in
bulk, decoupled from page loads.
"""

import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

DB_PATH = Path("cache/posters.db")

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
_TMDB_FIND_URL = "https://api.themoviedb.org/3/find/{}"
_TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w300{}"

# Failed lookups are cached too (NULL url) so a page load never repeatedly
# retries titles that don't resolve -- just retried occasionally.
_FAILURE_TTL = timedelta(hours=24)

# Live page renders only top up a small number of missing posters per call,
# so a cold cache can't turn into a multi-minute page load.
_LIVE_FETCH_BUDGET = 8
_LIVE_TIMEOUT = 3


def _ensure_table():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posters (
                tid TEXT PRIMARY KEY,
                poster_url TEXT,
                fetched_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _load_fresh(tids: list[str]) -> dict[str, str | None]:
    """Return {tid: url_or_None} for cached rows still within the failure
    TTL (a fresh NULL means "known unavailable, don't retry yet"). Rows
    older than the TTL, or absent entirely, are left out so callers treat
    them as needing a fetch."""
    if not tids:
        return {}
    placeholders = ",".join("?" * len(tids))
    cutoff = (datetime.now(timezone.utc) - _FAILURE_TTL).isoformat()
    with closing(sqlite3.connect(DB_PATH)) as conn:
        rows = conn.execute(
            f"""
            SELECT tid, poster_url FROM posters
            WHERE tid IN ({placeholders})
              AND (poster_url IS NOT NULL OR fetched_at > ?)
            """,
            [*tids, cutoff],
        ).fetchall()
    return {tid: url for tid, url in rows}


def _store(tid: str, url: str | None):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO posters (tid, poster_url, fetched_at) VALUES (?, ?, ?)",
            (tid, url, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def _fetch_poster_url(tid: str, timeout: int) -> str | None:
    if not TMDB_API_KEY:
        return None

    try:
        resp = requests.get(
            _TMDB_FIND_URL.format(tid),
            params={
                "external_source": "imdb_id",
                "api_key": TMDB_API_KEY,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None

    data = resp.json()
    results = data.get("movie_results") or data.get("tv_results") or []
    if not results or not results[0].get("poster_path"):
        return None

    return _TMDB_IMAGE_URL.format(results[0]["poster_path"])


def _fetch_and_store(tids: list[str], timeout: int) -> dict[str, str]:
    if not tids:
        return {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(
            zip(tids, pool.map(lambda t: _fetch_poster_url(t, timeout), tids))
        )
    for tid, url in results.items():
        _store(tid, url)
    return {tid: url for tid, url in results.items() if url}


def get_poster_urls(tids: list[str]) -> dict[str, str]:
    """Cache-first lookup for use in live page renders. Never blocks on
    more than _LIVE_FETCH_BUDGET network calls -- anything beyond that is
    left for the next render (or `warm_poster_cache.py`) to pick up."""
    _ensure_table()

    tids = list(dict.fromkeys(t for t in tids if t))
    fresh = _load_fresh(tids)
    resolved = {tid: url for tid, url in fresh.items() if url}

    missing = [t for t in tids if t not in fresh][:_LIVE_FETCH_BUDGET]
    resolved.update(_fetch_and_store(missing, _LIVE_TIMEOUT))

    return resolved


def warm_cache(tids: list[str], timeout: int = 5) -> dict[str, int]:
    """Bulk-resolve every not-yet-fresh tid, with no fetch budget cap.
    Intended for `warm_poster_cache.py`, not live page renders."""
    _ensure_table()

    tids = list(dict.fromkeys(t for t in tids if t))
    fresh = _load_fresh(tids)
    missing = [t for t in tids if t not in fresh]

    resolved = _fetch_and_store(missing, timeout)
    return {"checked": len(missing), "resolved": len(resolved)}
