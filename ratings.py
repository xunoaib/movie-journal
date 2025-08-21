from dataclasses import dataclass
from typing import Any, List

import pandas as pd
import polars as pl

from linker import get_default_mapper
from models import ImdbEntry

RATINGS_PATH = "imdb-data/title.ratings.tsv.gz"

CSV_OPTS: dict[str, Any] = {
    "separator": "\t",
    "null_values": ["\\N"],
    "infer_schema_length": 0,
    "quote_char": None,
    "has_header": True,
}


def collect_ratings(
    entries: List[ImdbEntry],
    ratings_path: str = RATINGS_PATH
) -> pd.DataFrame:
    ratings = pl.read_csv(ratings_path, **CSV_OPTS)
    entries_df = pl.DataFrame([e.__dict__ for e in entries])

    merged = entries_df.join(
        ratings, left_on="tid", right_on="tconst", how="left"
    )

    merged = merged.select(
        ["tid", "title", "year", "director", "averageRating", "numVotes"]
    )

    return merged.to_pandas()


if __name__ == "__main__":

    mapper = get_default_mapper()
    journal = mapper.load_journal()

    my_movies = [j.imdb for j in journal if j.imdb]

    df = collect_ratings(my_movies)
    print(df)
