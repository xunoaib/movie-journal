import csv

from models import ImdbEntry


def parse_imdb_movies(csv_fname):
    with open(csv_fname) as f:
        reader = csv.DictReader(f)
        movies = [
            ImdbEntry(
                tid=row['tconst'],
                title=row['title'],
                year=row['year'],
                director=row['directors'],
                composer=row['composers'],
            ) for row in reader
        ]
    return sorted(movies, key=lambda m: m.year)
