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
- Filter films by director
- Duplicate entry detection and missing IMDb identification

# Initial Setup

- Download the [IMDb Non-Commercial Datasets](https://developer.imdb.com/non-commercial-datasets/) to `./imdb-data/` (in `.tsv.gz` form)
- Run `python parse_tsv_gzs_to_csv.py` to generate `movie_directors.csv`
- Optionally run `python linker.py` to generate `cache/imdbs_grouped_by_title_year.pkl`
- Run `streamlit run movies.py` or `docker compose up` to serve the application
