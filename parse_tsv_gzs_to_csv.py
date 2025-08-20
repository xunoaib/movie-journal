'''
Parses IMDb datasets into a CSV containing: tid,title,year,directors
'''
import os

IMDB_DATA_DIR = 'data-link'


def main():
    import polars as pl

    current_dir = os.getcwd()
    os.chdir(IMDB_DATA_DIR)

    CSV_OPTS = dict(
        separator="\t",
        null_values=["\\N"],
        infer_schema_length=0,
        quote_char=None,
        has_header=True,
    )

    basics = (
        pl.scan_csv("title.basics.tsv.gz", **CSV_OPTS).filter(
            (pl.col("titleType") == "movie")
            & (pl.col("isAdult") == "0")
            & (pl.col("startYear").is_not_null())
        ).with_columns(
            pl.col("startYear").cast(pl.Int32).alias("year"),
            pl.col("primaryTitle").alias("title"),
        ).select(["tconst", "title", "year"])
    )

    crew = (
        pl.scan_csv("title.crew.tsv.gz",
                    **CSV_OPTS).select(["tconst", "directors"])
    )

    names = (
        pl.scan_csv("name.basics.tsv.gz",
                    **CSV_OPTS).select(["nconst", "primaryName"])
    )

    # explode directors safely (skip null/empty)
    exploded = (
        crew.filter(
            pl.col("directors").is_not_null()
            & (pl.col("directors") != "")
        ).with_columns(
            pl.col("directors").str.split(",")
        ).explode("directors").rename({
            "directors": "nconst"
        }).join(names, on="nconst",
                how="inner").rename({"primaryName": "director"})
    )

    movie_directors_exploded = basics.join(exploded, on="tconst", how="inner")

    movie_directors = (
        movie_directors_exploded.group_by(["tconst", "title", "year"]).agg(
            pl.col("director").sort().str.join(", ").alias("directors")
        )
    )

    # movie_directors_exploded.sink_csv("movie_directors_exploded.csv")
    movie_directors.sink_csv(current_dir + "/movie_directors.csv")


if __name__ == '__main__':
    main()
