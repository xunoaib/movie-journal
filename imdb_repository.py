import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from models import ImdbEntry, ProtoActor

DB_PATH = Path("cache/imdb_full.db")


class ImdbRepository:
    """Thin wrapper around the SQLite IMDb database for movie lookups."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._ensure_indexes()

    # ------------------------------------------------------------------
    def _execute(self, sql: str, params: tuple | list = ()):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(sql, params).fetchall()

    def _ensure_indexes(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
            # Speed up case-insensitive title searches
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_movies_primaryTitle_nocase "
                "ON Movies(primaryTitle COLLATE NOCASE)"
            )
            conn.commit()

    # ------------------------------------------------------------------
    #  Core lookups
    # ------------------------------------------------------------------
    def find_by_title_year(self, title: str, year: str | None) -> list[ImdbEntry]:
        """Return movies matching *title* (case-insensitive) and optional year."""
        sql = (
            "SELECT tconst, primaryTitle, startYear "
            "FROM Movies "
            "WHERE primaryTitle = ? COLLATE NOCASE "
            "  AND titleType IN ('movie', 'tvMovie') "
            "  AND isAdult = '0' "
            "  AND startYear IS NOT NULL"
        )
        params: list[str] = [title]
        if year is not None:
            sql += " AND startYear = ?"
            params.append(year)

        rows = self._execute(sql, params)
        return [self._row_to_entry(r) for r in rows]

    def find_by_tid(self, tid: str) -> ImdbEntry | None:
        """Return a single movie by its IMDb ID, or None."""
        rows = self._execute(
            "SELECT tconst, primaryTitle, startYear FROM Movies WHERE tconst = ?",
            (tid,),
        )
        if not rows:
            return None
        return self._row_to_entry(rows[0])

    # ------------------------------------------------------------------
    #  Bulk helpers
    # ------------------------------------------------------------------
    def find_actors_by_tids(self, tids: list[str]) -> dict[str, list[ProtoActor]]:
        """Return {tconst: [ProtoActor]} for the supplied TIDs."""
        if not tids:
            return {}

        placeholders = ",".join("?" * len(tids))
        rows = self._execute(
            f"""
            SELECT pr.tconst, p.nconst, p.primaryName
            FROM Principals pr
            JOIN People p ON pr.nconst = p.nconst
            WHERE pr.tconst IN ({placeholders})
              AND pr.category IN ('actor', 'actress')
            ORDER BY pr.tconst, pr.ordering
            """,
            tids,
        )

        film_actors: dict[str, list[ProtoActor]] = defaultdict(list)
        for row in rows:
            film_actors[row["tconst"]].append(
                ProtoActor(
                    nconst=row["nconst"], name=row["primaryName"], tids=[]
                )
            )
        return dict(film_actors)

    def find_ratings_by_tids(self, tids: list[str]) -> dict[str, dict]:
        """Return {tconst: {'averageRating': float, 'numVotes': int}}."""
        if not tids:
            return {}

        placeholders = ",".join("?" * len(tids))
        rows = self._execute(
            f"""
            SELECT tconst, averageRating, numVotes
            FROM Ratings
            WHERE tconst IN ({placeholders})
            """,
            tids,
        )

        return {
            row["tconst"]: {
                "averageRating": (
                    float(row["averageRating"])
                    if row["averageRating"] is not None
                    else None
                ),
                "numVotes": (
                    int(row["numVotes"])
                    if row["numVotes"] is not None
                    else None
                ),
            }
            for row in rows
        }

    def find_actor_filmographies(self, nconsts: list[str]) -> list[ProtoActor]:
        """Return ProtoActors with full filmographies for the given nconsts."""
        if not nconsts:
            return []

        placeholders = ",".join("?" * len(nconsts))
        rows = self._execute(
            f"""
            SELECT p.nconst, p.primaryName, pr.tconst
            FROM People p
            JOIN Principals pr ON p.nconst = pr.nconst
            WHERE p.nconst IN ({placeholders})
              AND pr.category IN ('actor', 'actress')
            ORDER BY p.nconst, pr.tconst
            """,
            nconsts,
        )

        actor_tids: dict[str, list[str]] = defaultdict(list)
        actor_names: dict[str, str] = {}
        for row in rows:
            nconst = row["nconst"]
            actor_names[nconst] = row["primaryName"]
            actor_tids[nconst].append(row["tconst"])

        return [
            ProtoActor(nconst=nconst, name=actor_names[nconst], tids=tids)
            for nconst, tids in actor_tids.items()
        ]

    def find_runtimes_by_tids(self, tids: list[str]) -> dict[str, int]:
        """Return {tconst: runtime_minutes} for movies that have one."""
        if not tids:
            return {}

        placeholders = ",".join("?" * len(tids))
        rows = self._execute(
            f"""
            SELECT tconst, runtimeMinutes
            FROM Movies
            WHERE tconst IN ({placeholders})
            """,
            tids,
        )

        result: dict[str, int] = {}
        for row in rows:
            val = row["runtimeMinutes"]
            if val and str(val).isdigit():
                result[row["tconst"]] = int(val)
        return result

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------
    def _row_to_entry(self, row: sqlite3.Row) -> ImdbEntry:
        tid = row["tconst"]
        return ImdbEntry(
            tid=tid,
            title=row["primaryTitle"],
            year=row["startYear"] or "",
            director=self._find_directors_by_tid(tid),
            composer=self._find_composers_by_tid(tid),
        )

    def _find_directors_by_tid(self, tid: str) -> str:
        rows = self._execute(
            "SELECT directors FROM Crew WHERE tconst = ?", (tid,)
        )
        if not rows or not rows[0]["directors"]:
            return ""
        return self._resolve_nconsts_to_names(rows[0]["directors"])

    def _find_composers_by_tid(self, tid: str) -> str:
        rows = self._execute(
            """
            SELECT p.primaryName
            FROM Principals pr
            JOIN People p ON pr.nconst = p.nconst
            WHERE pr.tconst = ? AND pr.category = 'composer'
            ORDER BY pr.ordering
            """,
            (tid,),
        )
        return ", ".join(row["primaryName"] for row in rows)

    def _resolve_nconsts_to_names(self, nconsts_str: str) -> str:
        nconsts = [n.strip() for n in nconsts_str.split(",") if n.strip()]
        if not nconsts:
            return ""
        placeholders = ",".join("?" * len(nconsts))
        rows = self._execute(
            f"SELECT nconst, primaryName FROM People WHERE nconst IN ({placeholders})",
            nconsts,
        )
        name_map = {row["nconst"]: row["primaryName"] for row in rows}
        return ", ".join(
            name_map.get(nconst, nconst) for nconst in nconsts
        )
