import csv

from models import ImdbEntry


def parse_imdb_movies(csv_fname):
    with open(csv_fname) as f:
        reader = csv.reader(f)
    movies = [ImdbEntry(*row) for row in reader]
    return sorted(movies, key=lambda m: m.year)
