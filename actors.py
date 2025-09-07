from collections import defaultdict
from typing import Dict, List, Tuple

import polars as pl

from linker import get_default_mapper
from models import JournalEntry

ACTORS_CSV = "cache/actors.csv"


def build_lookups(journal: List[JournalEntry]):
    """Return (actor_to_films, film_to_actors) lookups using IDs (not names)."""
    # load actor appearances
    actors = pl.read_csv(ACTORS_CSV)

    # filter actors to those with tids in the journal
    tids = [j.imdb.tid if j.imdb else j.tid for j in journal]
    actors = actors.filter(pl.col("tconst").is_in(tids))

    # film to actors
    film_lookup = actors.group_by("tconst").agg(
        pl.col("nconst").sort().alias("actors")
    ).to_dict(as_series=False)

    film_to_actors = {
        tid: film_lookup["actors"][i]
        for i, tid in enumerate(film_lookup["tconst"])
    }

    # actor to films
    actor_lookup = actors.group_by("nconst").agg(
        pl.col("tconst").sort().alias("films")
    ).to_dict(as_series=False)

    actor_to_films = {
        aid: actor_lookup["films"][i]
        for i, aid in enumerate(actor_lookup["nconst"])
    }

    # actor ID to name, and deduplicate in case of repeats across films
    actor_id_to_name = actors.select(["nconst", "actor"]
                                     ).unique().to_dict(as_series=False)

    actor_id_to_name = {
        actor_id_to_name["nconst"][i]: actor_id_to_name["actor"][i]
        for i in range(len(actor_id_to_name["nconst"]))
    }

    return actor_to_films, film_to_actors, actor_id_to_name


if __name__ == "__main__":
    mapper = get_default_mapper()
    journal = mapper.load_journal()

    actor_to_films, film_to_actors, actor_id_to_name = build_lookups(journal)
    film_tid_to_obj = {j.tid: j for j in journal}
    film_ids = [j.tid for j in journal]
    actor_films = defaultdict(set)

    for j in journal:
        # if j.tid not in film_to_actors:
        #     print('No actors for', j.tid)
        for actor_id in film_to_actors.get(j.tid, []):
            actor_films[actor_id].add(j.tid)

    actor_tids = sorted(
        actor_films.items(), key=lambda kv: (len(kv[1]), kv[0])
    )

    # for k, v in actor_tids:
    #     print(
    #         actor_id_to_name[k],
    #         len([film_tid_to_obj[t].imdb.title for t in v])
    #     )

    rows = []
    for actor_id, tids in actor_tids:
        films = [
            film_tid_to_obj[t].imdb.title for t in tids if t in film_tid_to_obj
        ]
        rows.append(
            {
                "actor_id": actor_id,
                "actor_name": actor_id_to_name.get(actor_id, None),
                "film_count": len(films),
                "films": films
            }
        )

    pl.Config.set_tbl_rows(-1)
    df = pl.DataFrame(rows)
    df = df.select(['actor_name', 'film_count'])
    print(df)
