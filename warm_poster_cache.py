"""Pre-populates cache/posters.db for every movie in the journal.

Run this once after deploying (and periodically after, e.g. via cron) so
the live app only ever needs cheap local cache reads to serve hover
previews -- no network calls happen during a page load.

    python warm_poster_cache.py
"""

import sys

from linker import get_default_mapper
from poster_cache import TMDB_API_KEY, warm_cache


def main():
    if not TMDB_API_KEY:
        sys.exit(
            "TMDB_API_KEY is not set. Get a free key at "
            "https://www.themoviedb.org/settings/api and set it as an "
            "environment variable."
        )

    movies = get_default_mapper().load_journal()
    tids = [m.tid for m in movies if m.tid]

    print(f"Resolving posters for {len(tids)} titles...", flush=True)
    stats = warm_cache(tids)
    print(
        f"Checked {stats['checked']} uncached/stale titles, "
        f"resolved {stats['resolved']} posters.",
        flush=True,
    )


if __name__ == "__main__":
    main()
