from typing import Dict, List

import polars as pl

from linker import get_default_mapper
from models import JournalEntry

ACTORS_CSV = "cache/actors.csv"


def build_actor_lookup(journal: List[JournalEntry]) -> Dict[str, list[str]]:
    """Return dict mapping tid → list of actor names"""
    # Load actor appearances
    actors = pl.read_csv(ACTORS_CSV)

    tids = [j.imdb.tid if j.imdb else j.tid for j in journal]
    actors = actors.filter(pl.col("tconst").is_in(tids))

    # Group by tid -> collect actors
    lookup = (
        actors.group_by("tconst").agg(pl.col("actor").sort().alias("actors")
                                      ).to_dict(as_series=False)
    )

    # Convert into {tid: [actor1, actor2, ...]}
    tid_to_actors = {
        tid: lookup["actors"][i]
        for i, tid in enumerate(lookup["tconst"])
    }
    return tid_to_actors


if __name__ == "__main__":
    mapper = get_default_mapper()
    journal = mapper.load_journal()

    actor_lookup = build_actor_lookup(journal)
    for tid, actors in actor_lookup.items():
        print(tid, ":", actors)

    print(len(actor_lookup))
