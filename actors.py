from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

import polars as pl

from linker import get_default_mapper
from models import JournalEntry, ProtoActor

ACTORS_CSV = "cache/actors.csv"
ACTORS_CACHE = "cache/actor_mappings.pkl"


def parse_proto_actors():
    actors = pl.read_csv(ACTORS_CSV)
    grouped = actors.group_by("nconst").agg(
        pl.col("actor").first().alias("actor"),
        pl.col("tconst").sort().alias("films"),
    ).sort('nconst')

    return [
        ProtoActor(row['nconst'], row['actor'], row['films'])
        for row in grouped.iter_rows(named=True)
    ]


def group_actors_by_journal(
    actors: list[ProtoActor],
    journal: List[JournalEntry],
):
    wanted = {j.tid or (j.imdb.tid if j.imdb else None)
              for j in journal} - {None}
    film_actors = {}

    for a in actors:
        for t in a.tids:
            if t in wanted:
                film_actors.setdefault(t, []).append(a)

    return film_actors


if __name__ == "__main__":
    proto_actors = parse_proto_actors()
    mapper = get_default_mapper()
    journal = mapper.load_journal()
    film_actors = group_actors_by_journal(proto_actors, journal)
    print(film_actors['tt2125490'])
