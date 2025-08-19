import pickle
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from models import ImdbEntry, LogEntry
from parsers.imdb import parse_imdb_movies
from parsers.log import parse_movie_log

MOVIE_JOURNAL = 'movie_journal.txt'
IMDB_CSV = 'movie_directors.csv'
CACHE_FILE = 'cache/imdbs_grouped_by_title_year.pkl'


class ImdbTidMapper:
    '''
    Handles:
    - Parsing IMDb data and grouping by (title, year)
    - Caching the grouped results to disk
    - Assigning TIDs to a journal of log entries
    '''

    def __init__(
        self,
        imdb_csv: str,
        cache_file: str,
        journal_file: str,
    ):
        self.imdb_csv = Path(imdb_csv)
        self.cache_file = Path(cache_file)
        self.journal_file = Path(journal_file)

        # lazy load mappings
        self._mappings: dict[tuple[str, str | None],
                             list[ImdbEntry]] | None = None

    def _group_by_title_year(self, imdbs: list[ImdbEntry]):
        '''Group ImdbEntries by (title.lower(), year).'''
        d = defaultdict(list)
        for m in imdbs:
            d[m.title.lower(), m.year].append(m)
        return d

    def _load_or_generate_mappings(self):
        '''Load grouped IMDb data from cache, or regenerate if missing.'''
        if self._mappings is not None:
            return self._mappings

        if self.cache_file.exists():
            print('Loading IMDb mappings from cache...')
            with open(self.cache_file, 'rb') as f:
                self._mappings = pickle.load(f)
        else:
            print('Parsing IMDb CSV...')
            imdbs = parse_imdb_movies(self.imdb_csv)

            print('Creating mapping...')
            self._mappings = self._group_by_title_year(imdbs)

            print(f'Pickling mappings to {self.cache_file}...')
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self._mappings, f)

        return self._mappings

    def assign_tids(self, journal: list[LogEntry]) -> list[LogEntry]:
        '''Supplement journal entries with TIDs from IMDb based on (title, year).'''
        if all(j.tid is not None for j in journal):
            return journal

        mappings = self._load_or_generate_mappings()
        output = []

        for j in journal:
            if j.tid is None:
                if matches := mappings.get((j.title.lower(), j.year)):
                    assert len(
                        matches
                    ) == 1, f'Multiple IMDb IDs found for {j.title}'
                    j = LogEntry(**asdict(j) | {'tid': matches[0].tid})
            output.append(j)

        return output

    def parse_journal(self) -> list[LogEntry]:
        '''Parse the journal file into log entries.'''
        return parse_movie_log(self.journal_file)


def get_default_mapper() -> ImdbTidMapper:
    return ImdbTidMapper(
        imdb_csv=IMDB_CSV,
        cache_file=CACHE_FILE,
        journal_file=MOVIE_JOURNAL,
    )


def debug_unmatched(mapper: ImdbTidMapper):
    '''Print journal entries that don’t have a matching IMDb entry.'''
    journal = mapper.parse_journal()
    mappings = mapper._load_or_generate_mappings()

    for j in journal:
        if not mappings.get((j.title.lower(), j.year)):
            print('No matches for', j.title)


def main():
    mapper = get_default_mapper()
    journal = mapper.parse_journal()
    updated = mapper.assign_tids(journal)
    debug_unmatched(mapper)


if __name__ == '__main__':
    main()
