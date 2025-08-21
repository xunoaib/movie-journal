# Initial Setup

- Download the [IMDb Non-Commercial Datasets](https://developer.imdb.com/non-commercial-datasets/) to `./imdb-data/` (in `.tsv.gz` form)
- Run `python parse_tsv_gzs_to_csv.py` to generate `movie_directors.csv`
- Optionally run `python linker.py` to generate `cache/imdbs_grouped_by_title_year.pkl`
- Run `streamlit run movies.py` or `docker compose up` to serve the application
