'''
This module:
- Assigns TIDs to a list of journal entries (using IMDb data)
- Groups a list of ImdbEntries by (year, title)
- Caches the above groups to a pickled cache.
'''

import pickle
from collections import defaultdict
from dataclasses import asdict
from functools import cache
from pathlib import Path

from models import ImdbEntry, LogEntry
from parsers.imdb import parse_imdb_movies
from parsers.log import parse_movie_log

IMDB_CSV_IN = 'movie_directors.csv'
TITLEYEAR_CACHE_OUT = 'cache/imdbs_grouped_by_title_year.pkl'
JOURNAL_IN = 'movie_journal.txt'


def group_imdb_by_title_year(imdbs: list[ImdbEntry]):
    '''Group ImdbEntries by (title, year)'''

    d = defaultdict(list)
    for m in imdbs:
        d[m.title.lower(), m.year].append(m)
    return d


def load_or_generate_groups(cache_file: str):
    '''Groups ImdbEntries by (title, year). Reads from cache if available.'''

    if Path(cache_file).exists():
        print('Loading from cache...')
        return pickle.load(open(cache_file, 'rb'))

    imdbs = parse_imdb_movies(IMDB_CSV_IN)

    print('Creating mapping...')
    mappings = group_imdb_by_title_year(imdbs)

    print('Pickling to file...')
    with open(cache_file, 'wb') as f:
        pickle.dump(mappings, f)

    return mappings


def assign_tids_to_journal(journal: list[LogEntry]) -> list[LogEntry]:
    '''Supplement journal entries with tids from IMDb based on (title, year)'''

    # Every film has a TID. No need to continue.
    if all(j.tid is not None for j in journal):
        return journal

    mappings = load_or_generate_groups(TITLEYEAR_CACHE_OUT)

    output = []
    for j in journal:
        if j.tid is None:
            if matches := mappings.get((j.title.lower(), j.year)):
                assert len(
                    matches
                ) == 1, 'Multiple IMDb IDs found for journal entry'
                j = LogEntry(**asdict(j) | {'tid': matches[0].tid})
        output.append(j)
    return output


def main_test():
    # Group IMDB movies by (title, year)
    mappings = load_or_generate_groups(TITLEYEAR_CACHE_OUT)

    # Parse journal
    journal = parse_movie_log(JOURNAL_IN)

    for j in journal:
        if matches := mappings.get((j.title.lower(), j.year)):
            pass
        else:
            print('No matches for', j.title)


if __name__ == '__main__':
    main_test()
