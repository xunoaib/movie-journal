from dataclasses import replace
import warnings
from pathlib import Path

from imdb_repository import ImdbRepository
from models import JournalEntry
from parsers.log import parse_movie_log

MOVIE_JOURNAL = 'movie_journal.txt'


class ImdbTidMapper:
    '''
    Handles:
    - Querying IMDb data from the SQLite database
    - Assigning TIDs to a journal of log entries
    - Enriching journal entries with full IMDb metadata
    '''

    def __init__(
        self,
        journal_file: str,
        db_path: str | None = None,
    ):
        self.journal_file = Path(journal_file)
        self.repo = ImdbRepository(Path(db_path)) if db_path else ImdbRepository()

    def assign_tids(self, journal: list[JournalEntry]) -> list[JournalEntry]:
        '''Supplement journal entries with TIDs from IMDb based on (title, year).'''
        if all(j.tid is not None for j in journal):
            return journal

        output = []
        for j in journal:
            if j.tid is not None:
                output.append(j)
                continue

            matches = self.repo.find_by_title_year(j.title, j.year)
            if len(matches) == 1:
                output.append(replace(j, _tid=matches[0].tid))
            elif len(matches) > 1:
                warnings.warn(
                    f"Multiple IMDb IDs found for {j.title!r} ({j.year}): "
                    f"{[m.tid for m in matches]}"
                )
                output.append(j)
            else:
                output.append(j)

        return output

    def assign_imdbs(self, journal: list[JournalEntry]) -> list[JournalEntry]:
        '''Assign IMDb entries to JournalEntrys based on TID.'''
        output = []
        for j in journal:
            if j.imdb is None and j.tid:
                if entry := self.repo.find_by_tid(j.tid):
                    output.append(replace(j, imdb=entry))
                else:
                    output.append(j)
            else:
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
    return ImdbTidMapper(journal_file=MOVIE_JOURNAL)


def main():
    mapper = get_default_mapper()
    journal = mapper.load_journal()

    for j in journal:
        if j.imdb:
            print(j.title, j.imdb)


if __name__ == '__main__':
    main()
