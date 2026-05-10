from collections import defaultdict
from typing import Dict, List

from imdb_repository import ImdbRepository
from models import JournalEntry, ProtoActor


def parse_proto_actors(filter_by_tids: set[str]) -> list[ProtoActor]:
    """
    Return all actors who appear in *any* of the given TIDs,
    each with their complete filmography.
    """
    if not filter_by_tids:
        return []

    repo = ImdbRepository()

    # Step 1: find every actor who appears in the journal films
    film_actors = repo.find_actors_by_tids(list(filter_by_tids))
    nconsts = list({a.nconst for actors in film_actors.values() for a in actors})

    if not nconsts:
        return []

    # Step 2: fetch their full filmographies in one query
    return repo.find_actor_filmographies(nconsts)


def group_actors_by_journal(
    actors: list[ProtoActor],
    journal: List[JournalEntry],
) -> dict[str, list[ProtoActor]]:
    """Map each journal TID to the list of actors who appear in it."""

    wanted = {j.tid or (j.imdb.tid if j.imdb else None)
              for j in journal} - {None}

    film_actors: dict[str, list[ProtoActor]] = {}

    for a in actors:
        for t in a.tids:
            if t in wanted:
                film_actors.setdefault(t, []).append(a)

    return film_actors


def group_actors_by_journal_cached(
    actors: list[ProtoActor],
    journal: List[JournalEntry],
) -> dict[str, list[ProtoActor]]:
    """Legacy shim — caching is now handled at the DB layer."""
    return group_actors_by_journal(actors, journal)
