import pickle
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from models import ImdbEntry, JournalEntry
from parsers.imdb import parse_imdb_movies
from parsers.log import parse_movie_log

MOVIE_JOURNAL = 'movie_journal.txt'
IMDB_CSV = 'cache/movie_directors.csv'
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
        self._title_year_mappings: dict[tuple[str, str | None],
                                        list[ImdbEntry]] | None = None
        self._tid_imdbs: dict[str, ImdbEntry] = {}

    def _group_by_title_year(self, imdbs: list[ImdbEntry]):
        '''Group ImdbEntries by (title.lower(), year).'''
        d = defaultdict(list)
        for m in imdbs:
            d[m.title.lower(), m.year].append(m)
        return d

    def _load_or_generate_title_year_mappings(self):
        '''Load grouped IMDb data from cache, or regenerate if missing.'''
        if self._title_year_mappings is not None:
            return self._title_year_mappings

        if self.cache_file.exists():
            print('Loading IMDb mappings from cache...')
            with open(self.cache_file, 'rb') as f:
                data = pickle.load(f)
                self._title_year_mappings = data['title_year_mappings']
                self._tid_imdbs = data['tid_imdbs']
        else:
            print('Parsing IMDb CSV...')
            imdbs = parse_imdb_movies(self.imdb_csv)

            print('Creating mappings...')
            self._title_year_mappings = self._group_by_title_year(imdbs)
            self._tid_imdbs = {m.tid: m for m in imdbs}

            print(f'Pickling mappings to {self.cache_file}...')
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'wb') as f:
                data = {
                    'title_year_mappings': self._title_year_mappings,
                    'tid_imdbs': self._tid_imdbs,
                }
                pickle.dump(data, f)

        return self._title_year_mappings

    def assign_tids(self, journal: list[JournalEntry]) -> list[JournalEntry]:
        '''Supplement journal entries with TIDs from IMDb based on (title, year).'''
        if all(j.tid is not None for j in journal):
            return journal

        mappings = self._load_or_generate_title_year_mappings()
        output = []

        for j in journal:
            if j.tid is None:
                if matches := mappings.get((j.title.lower(), j.year)):
                    assert len(
                        matches
                    ) == 1, f'Multiple IMDb IDs found for {j.title}: {matches}'
                    j = JournalEntry(**asdict(j) | {'_tid': matches[0].tid})
            output.append(j)

        return output

    def assign_imdbs(self, journal: list[JournalEntry]) -> list[JournalEntry]:
        '''Assign IMDb entries to JournalEntrys based on TID'''

        output = []
        for j in journal:
            if j.imdb is None and j.tid and (m := self._tid_imdbs.get(j.tid)):
                j = JournalEntry(**(asdict(j) | {'imdb': m}))
            output.append(j)
        return output

    def parse_raw_journal(self) -> list[JournalEntry]:
        '''Parse the raw journal file as-is into log entries, without IMDb correlation.'''
        return parse_movie_log(self.journal_file)

    def load_journal(self) -> list[JournalEntry]:
        '''Parse the journal file into log entries and perform IMDb correlation.'''
        journal = self.parse_raw_journal()
        journal = self.assign_tids(journal)
        journal = self.assign_imdbs(journal)
        return journal


def get_default_mapper() -> ImdbTidMapper:
    return ImdbTidMapper(
        imdb_csv=IMDB_CSV,
        cache_file=CACHE_FILE,
        journal_file=MOVIE_JOURNAL,
    )


def main():
    mapper = get_default_mapper()
    journal = mapper.load_journal()

    for j in journal:
        # if not mappings.get((j.title.lower(), j.year)):
        #     print('No matches for', j.title)
        if j.imdb:
            print(j.title, j.imdb)
        pass


if __name__ == '__main__':
    main()
