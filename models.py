from dataclasses import dataclass


@dataclass(frozen=True)
class ImdbEntry:
    tid: str
    title: str
    year: str
    director: str
    composer: str

    def __eq__(self, other):
        if not isinstance(other, ImdbEntry):
            return NotImplementedError
        return self.tid == other.tid

    def __hash__(self):
        return hash(self.tid)


@dataclass(frozen=True)
class JournalEntry:
    position: int
    subnum: int  # subnumber, to disambiguate multiple films on the same line
    title: str
    mark: str | None
    year: str | None
    _tid: str | None  # IMDb TID
    backfill: str | None
    imdb: ImdbEntry | None = None

    @property
    def tid(self):
        return self.imdb.tid if (self.imdb and self.imdb.tid) else self._tid

    def __eq__(self, other):
        if not isinstance(other, JournalEntry):
            return NotImplementedError
        return all(
            [
                self.position == other.position,
                self.subnum == self.subnum,
                self.title == other.title,
            ]
        )

    def __hash__(self):
        return hash((self.position, self.subnum, self.title))

    @property
    def starred(self):
        return self.mark == '⭐'

    @property
    def checked(self):
        return self.mark == '✅'


@dataclass
class ProtoActor:
    nconst: str
    name: str
    tids: list[str]
