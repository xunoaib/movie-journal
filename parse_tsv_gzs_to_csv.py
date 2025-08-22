import os
from pathlib import Path
from typing import Any

IMDB_DATA_DIR = 'imdb-data'
OUTPUT_CSV = Path('cache/movie_directors.csv')
ACTORS_CSV = Path('cache/actors.csv')


class ImdbPaths:

    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)

    def file(self, name: str) -> str:
        return os.path.join(self.base_dir, name)

    @property
    def basics(self) -> str:
        return self.file("title.basics.tsv.gz")

    @property
    def crew(self) -> str:
        return self.file("title.crew.tsv.gz")

    @property
    def names(self) -> str:
        return self.file("name.basics.tsv.gz")

    @property
    def principals(self) -> str:
        return self.file("title.principals.tsv.gz")


def main():
    import polars as pl

    paths = ImdbPaths(IMDB_DATA_DIR)

    CSV_OPTS: dict[str, Any] = {
        "separator": "\t",
        "null_values": ["\\N"],
        "infer_schema_length": 0,
        "quote_char": None,
        "has_header": True,
    }

    print('Parsing movies from IMDb tsv.gzs...')
    basics = (
        pl.scan_csv(paths.basics, **CSV_OPTS).filter(
            (
                (pl.col("titleType") == "movie")
                | (pl.col("titleType") == "tvMovie")
            )
            & (pl.col("isAdult") == "0")
            & (pl.col("startYear").is_not_null())
        ).with_columns(
            pl.col("startYear").cast(pl.Int32).alias("year"),
            pl.col("primaryTitle").alias("title"),
        ).select(["tconst", "title", "year"])
    )

    crew = pl.scan_csv(paths.crew, **CSV_OPTS).select(["tconst", "directors"])
    names = pl.scan_csv(paths.names,
                        **CSV_OPTS).select(["nconst", "primaryName"])

    # Directors
    exploded_directors = (
        crew.filter(
            pl.col("directors").is_not_null() & (pl.col("directors") != "")
        ).with_columns(
            pl.col("directors").str.split(",")
        ).explode("directors").rename({
            "directors": "nconst"
        }).join(names, on="nconst",
                how="inner").rename({"primaryName": "director"})
    )
    movie_directors = basics.join(exploded_directors, on="tconst", how="inner")
    movie_directors = (
        movie_directors.group_by(["tconst", "title", "year"]).agg(
            pl.col("director").sort().str.join(", ").alias("directors")
        )
    )

    # Composers from principals
    principals_composer = (
        pl.scan_csv(paths.principals, **CSV_OPTS).filter(
            pl.col("category") == "composer"
        ).select(["tconst", "nconst"]
                 ).join(names, on="nconst",
                        how="inner").rename({"primaryName": "composer"})
    )
    movie_composers = basics.join(
        principals_composer, on="tconst", how="inner"
    )
    movie_composers = (
        movie_composers.group_by(["tconst", "title", "year"]).agg(
            pl.col("composer").sort().str.join(", ").alias("composers")
        )
    )

    # --- Actors from principals ---
    principals_actor = (
        pl.scan_csv(paths.principals, **CSV_OPTS).filter(
            (pl.col("category") == "actor")
            | (pl.col("category") == "actress")
        ).select(["tconst", "nconst"]
                 ).join(names, on="nconst",
                        how="inner").rename({"primaryName": "actor"})
    )

    # Per-movie aggregation (actors column)
    movie_actors = basics.join(principals_actor, on="tconst", how="inner")
    movie_actors = (
        movie_actors.group_by(["tconst", "title", "year"]).agg(
            pl.col("actor").sort().str.join(", ").alias("actors")
        )
    )

    # Merge movies + directors + composers + actors
    movies = (
        movie_directors.join(
            movie_composers.select(["tconst", "composers"]),
            on="tconst",
            how="left"
        ).join(
            movie_actors.select(["tconst", "actors"]), on="tconst", how="left"
        )
    )

    OUTPUT_CSV.parent.mkdir(exist_ok=True)
    print('Writing to CSV:', OUTPUT_CSV)
    movies.sink_csv(OUTPUT_CSV)

    # --- Actor appearances file ---
    actor_appearances = (
        principals_actor.join(basics, on="tconst", how="inner").select(
            ["nconst", "actor", "tconst", "title", "year"]
        ).sort(["actor", "year"])
    )

    print('Writing to CSV:', ACTORS_CSV)
    actor_appearances.sink_csv(ACTORS_CSV)


if __name__ == '__main__':
    main()
