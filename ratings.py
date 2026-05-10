import pandas as pd

from imdb_repository import ImdbRepository
from linker import get_default_mapper


def collect_ratings(tids: list[str]) -> pd.DataFrame:
    repo = ImdbRepository()
    ratings = repo.find_ratings_by_tids(tids)

    df = pd.DataFrame(
        [
            {
                "tid": tid,
                "averageRating": r["averageRating"],
                "numVotes": r["numVotes"],
            }
            for tid, r in ratings.items()
        ]
    )
    return df.sort_values(by="averageRating", ascending=False)


if __name__ == "__main__":
    mapper = get_default_mapper()
    journal = mapper.load_journal()

    tids = [j.tid for j in journal if j.tid]
    df = collect_ratings(tids)

    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", None)
    pd.set_option("display.max_columns", None)

    print(df)
