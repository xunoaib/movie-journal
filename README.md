# 🎬 Movie Journal

An interactive **Streamlit web app** for cataloguing your personal movie-watching
history! This project allows you to display and navigate your list of watched
films, link them to IMDb, and view breakdowns by year, director, and personal
ratings, with clean visualizations and interactive filters.

## ✨ Features
- Search by title or year
- Filter by marks (⭐, ✅, 💣, or none)
- Clickable IMDb links
- Exportable table view
- Histogram of films by release year
- Filter films by director, composer, and actor
- Duplicate entry detection and missing IMDb identification

# Initial Setup

- Download the [IMDb Non-Commercial Datasets](https://developer.imdb.com/non-commercial-datasets/) to `./imdb-data/` (in `.tsv.gz` form)
- Run `python parse_tsv_to_sqlite.py` to build `cache/imdb_full.db`
- Run `streamlit run movies.py` or `docker compose up` to serve the application

## Architecture

The app now uses a **SQLite-backed repository** (`imdb_repository.py`) instead of
CSV + pickle intermediates:

- `parse_tsv_to_sqlite.py` imports raw IMDb `.tsv.gz` files into `cache/imdb_full.db`
- `linker.py` queries the database on demand to match journal titles to IMDb TIDs
- `actors.py` pulls actor filmographies directly from the `Principals` and `People` tables
- `movies.py` lazily loads actor data only when the *Actors* tab is opened

Ambiguous title matches are written to `cache/ambiguous_matches.json` for manual review.
