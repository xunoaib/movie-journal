import os
import sqlite3
from pathlib import Path

import pandas as pd

IMDB_DATA_DIR = "imdb-data"
DB_PATH = Path("cache/imdb_full.db")


class ImdbPaths:

    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)

    def file(self, name: str) -> str:
        return os.path.join(self.base_dir, name)

    @property
    def akas(self):
        return self.file("title.akas.tsv.gz")

    @property
    def basics(self):
        return self.file("title.basics.tsv.gz")

    @property
    def crew(self):
        return self.file("title.crew.tsv.gz")

    @property
    def episode(self):
        return self.file("title.episode.tsv.gz")

    @property
    def principals(self):
        return self.file("title.principals.tsv.gz")

    @property
    def ratings(self):
        return self.file("title.ratings.tsv.gz")

    @property
    def names(self):
        return self.file("name.basics.tsv.gz")


def build_database():
    paths = ImdbPaths(IMDB_DATA_DIR)
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Drop and recreate schema
    cur.executescript(
        """
    DROP TABLE IF EXISTS Akas;
    DROP TABLE IF EXISTS Movies;
    DROP TABLE IF EXISTS Crew;
    DROP TABLE IF EXISTS Episodes;
    DROP TABLE IF EXISTS Principals;
    DROP TABLE IF EXISTS Ratings;
    DROP TABLE IF EXISTS People;

    CREATE TABLE Akas (
        titleId TEXT,
        ordering INTEGER,
        title TEXT,
        region TEXT,
        language TEXT,
        types TEXT,
        attributes TEXT,
        isOriginalTitle INTEGER
    );

    CREATE TABLE Movies (
        tconst TEXT PRIMARY KEY,
        titleType TEXT,
        primaryTitle TEXT,
        originalTitle TEXT,
        isAdult INTEGER,
        startYear TEXT,
        endYear TEXT,
        runtimeMinutes TEXT,
        genres TEXT
    );

    CREATE TABLE Crew (
        tconst TEXT,
        directors TEXT,
        writers TEXT
    );

    CREATE TABLE Episodes (
        tconst TEXT,
        parentTconst TEXT,
        seasonNumber TEXT,
        episodeNumber TEXT
    );

    CREATE TABLE Principals (
        tconst TEXT,
        ordering INTEGER,
        nconst TEXT,
        category TEXT,
        job TEXT,
        characters TEXT
    );

    CREATE TABLE Ratings (
        tconst TEXT,
        averageRating REAL,
        numVotes INTEGER
    );

    CREATE TABLE People (
        nconst TEXT PRIMARY KEY,
        primaryName TEXT,
        birthYear TEXT,
        deathYear TEXT,
        primaryProfession TEXT,
        knownForTitles TEXT
    );
    """
    )
    conn.commit()

    # --- Helper: stream TSV into SQLite ---
    def import_tsv(path, table, usecols=None):
        print(f"Loading {table}...")
        for chunk in pd.read_csv(
            path,
            sep="\t",
            na_values="\\N",
            dtype=str,
            low_memory=False,
            chunksize=100_000,
            usecols=usecols,
        ):
            chunk.to_sql(table, conn, if_exists="append", index=False)

    # Load each dataset
    import_tsv(paths.akas, "Akas")
    import_tsv(paths.basics, "Movies")
    import_tsv(paths.crew, "Crew")
    import_tsv(paths.episode, "Episodes")
    import_tsv(paths.principals, "Principals")
    import_tsv(paths.ratings, "Ratings")
    import_tsv(paths.names, "People")

    # Indexes for speed (after bulk insert)
    print("Creating indexes...")
    cur.executescript(
        """
    CREATE INDEX idx_movies_year ON Movies(startYear);
    CREATE INDEX idx_movies_title ON Movies(primaryTitle);
    CREATE INDEX idx_crew_tconst ON Crew(tconst);
    CREATE INDEX idx_principals_tconst ON Principals(tconst);
    CREATE INDEX idx_principals_nconst ON Principals(nconst);
    CREATE INDEX idx_ratings_tconst ON Ratings(tconst);
    CREATE INDEX idx_people_name ON People(primaryName);
    """
    )
    conn.commit()
    conn.close()
    print(f"✅ Full IMDb database built at {DB_PATH}")


if __name__ == "__main__":
    build_database()
