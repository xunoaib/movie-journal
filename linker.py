import pickle
from dataclasses import asdict
from functools import cache
from pathlib import Path

from models import ImdbEntry, LogEntry


def link_imdbs(journal: list[LogEntry]):
    '''Assign missing IMDb IDs to log entries based on title and date'''

    output = []
    for j in journal:
        if j.tid is None:
            if ms := journal_to_tids(j):
                assert len(
                    ms
                ) == 1, 'Multiple IMDb IDs found for journal entry'
                j = LogEntry(**asdict(j) | {'tid': ms[0].tid})
        output.append(j)
    return output


@cache
def journal_matches_cache(
    cache='parse_imdb_matches.pkl'
) -> dict[LogEntry, list[ImdbEntry]]:
    cache = Path(cache)
    if cache.exists():
        print('Loading matches')
        j_matches = pickle.load(open(cache, 'rb'))
    else:
        # print('Generating and caching matches...')
        # j_matches = parse_imdb.generate_matches(journal, imdbs)
        # pickle.dump(j_matches, open(cache, 'wb'))
        raise FileNotFoundError(
            'Journal to IMDb matchings cache file not found.'
        )
    return j_matches
    return pickle.load(open('parse_imdb_matches.pkl', 'rb'))


def journal_to_tids(log: LogEntry):
    cache = journal_matches_cache()
    return cache.get(log)
