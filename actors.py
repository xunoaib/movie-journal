from typing import Dict, List, Tuple

import polars as pl

from linker import get_default_mapper
from models import JournalEntry

ACTORS_CSV = "cache/actors.csv"


def build_lookups(
    journal: List[JournalEntry]
) -> Tuple[Dict[str, list[str]], Dict[str, list[str]]]:
    """Return (actor_to_films, film_to_actors) lookups using IDs (not names)."""
    # Load actor appearances
    actors = pl.read_csv(ACTORS_CSV)

    # Restrict to only tids in journal
    tids = [j.imdb.tid if j.imdb else j.tid for j in journal]
    actors = actors.filter(pl.col("tconst").is_in(tids))

    # --- film → actors ---
    film_lookup = (
        actors.group_by("tconst").agg(pl.col("nconst").sort().alias("actors")
                                      ).to_dict(as_series=False)
    )
    film_to_actors = {
        tid: film_lookup["actors"][i]
        for i, tid in enumerate(film_lookup["tconst"])
    }

    # --- actor → films ---
    actor_lookup = (
        actors.group_by("nconst").agg(pl.col("tconst").sort().alias("films")
                                      ).to_dict(as_series=False)
    )
    actor_to_films = {
        aid: actor_lookup["films"][i]
        for i, aid in enumerate(actor_lookup["nconst"])
    }

    return actor_to_films, film_to_actors


if __name__ == "__main__":
    mapper = get_default_mapper()
    journal = mapper.load_journal()

    actor_to_films, film_to_actors = build_lookups(journal)

    print("Film → Actors")
    for tid, actor_ids in film_to_actors.items():
        print(tid, ":", actor_ids)

    print()
    print("Actor → Films")
    for nconst, film_ids in actor_to_films.items():
        print(nconst, ":", film_ids)

    print()
    print("Total films:", len(film_to_actors))
    print("Total actors:", len(actor_to_films))
