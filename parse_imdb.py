import pickle
from collections import defaultdict
from pathlib import Path

from models import ImdbEntry, LogEntry
from parsers.imdb import parse_imdb_movies
from parsers.log import parse_movie_log


def generate_matches(journal: list[LogEntry], movies: list[ImdbEntry]):
    j_matches = {j: [] for j in journal}
    for m in movies:
        for j in journal:
            if j.title == m.title and j.year == m.year:
                if j.tid is None or j.tid == m.tid:
                    j_matches[j].append(m)
    return j_matches


def main():
    journal = parse_movie_log('movie_journal.txt')
    imdbs = parse_imdb_movies('data/movie_directors.csv')

    find_matches(journal, imdbs)


def find_matches(journal: list[LogEntry], imdbs: list[ImdbEntry]):

    cache = Path('parse_imdb_matches.pkl')
    if cache.exists():
        print('Loading matches')
        j_matches = pickle.load(open(cache, 'rb'))
    else:
        print('Generating and caching matches...')
        j_matches = generate_matches(journal, imdbs)
        pickle.dump(j_matches, open(cache, 'wb'))

    for j, matches in j_matches.items():
        if len(matches) > 1:
            print(f'# {j.title}')
            for m in matches:
                print(f'  {m}')
            print()


if __name__ == '__main__':
    main()
