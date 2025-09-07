import pickle
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import polars as pl

from linker import get_default_mapper
from models import JournalEntry, ProtoActor

ACTORS_CSV = "cache/actors.csv"


def parse_proto_actors(filter_by_tids: set[str]):
    PROTO_ACTORS_CACHE = Path('cache/proto_actors.pkl')
    if PROTO_ACTORS_CACHE.exists():
        print('Parsing proto actors from cache...')
        with open(PROTO_ACTORS_CACHE, 'rb') as f:
            return pickle.load(f)

    def acquire():
        actors = pl.read_csv(ACTORS_CSV)
        grouped = actors.group_by("nconst").agg(
            pl.col("actor").first().alias("actor"),
            pl.col("tconst").sort().alias("films"),
        ).sort('nconst')

        data = [
            ProtoActor(row['nconst'], row['actor'], row['films'])
            for row in grouped.to_dicts()
        ]

        tids_set = set(filter_by_tids)
        data = [actor for actor in data if tids_set & set(actor.tids)]
        return data

    data = acquire()
    with open(PROTO_ACTORS_CACHE, 'wb') as f:
        pickle.dump(data, f)

    return data


def group_actors_by_journal_cached(
    actors: list[ProtoActor],
    journal: List[JournalEntry],
) -> dict[str, list[ProtoActor]]:
    GROUPED_ACTORS_CACHE = Path('cache/grouped_actors_by_journal.pkl')
    if GROUPED_ACTORS_CACHE.exists():
        print('Loading grouped actors from cache...', flush=True)
        with open(GROUPED_ACTORS_CACHE, 'rb') as f:
            return pickle.load(f)
    else:
        print('Regenerating grouped actors', flush=True)
        grouped = group_actors_by_journal(proto_actors, journal)
        with open(GROUPED_ACTORS_CACHE, 'wb') as f:
            pickle.dump(grouped, f)
        return grouped


def group_actors_by_journal(
    actors: list[ProtoActor],
    journal: List[JournalEntry],
):

    wanted = {j.tid or (j.imdb.tid if j.imdb else None)
              for j in journal} - {None}

    film_actors: dict[str, list[ProtoActor]] = {}

    for a in actors:
        for t in a.tids:
            if t in wanted:
                film_actors.setdefault(t, []).append(a)

    return film_actors


if __name__ == "__main__":
    print('Loading journal...')
    mapper = get_default_mapper()
    journal = mapper.load_journal()

    print('Parsing proto actors...')
    tids = list(
        {j.tid or (j.imdb.tid if j.imdb else None)
         for j in journal} - {None}
    )
    proto_actors = parse_proto_actors(tids)

    print('Grouping...')
    # film_actors = group_actors_by_journal(proto_actors, journal)
    film_actors = group_actors_by_journal_cached(proto_actors, journal)

    for actor in film_actors['tt0043465']:
        print(actor.name)
