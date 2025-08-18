from dataclasses import dataclass


@dataclass(frozen=True)
class LogEntry:
    position: int
    subnum: int  # subnumber, to disambiguate multiple films on the same line
    title: str
    mark: str | None
    year: str | None

    def __eq__(self, other):
        if not isinstance(other, LogEntry):
            return NotImplementedError
        return self.position == other.position and self.subnum == self.subnum

    def __hash__(self):
        return hash(self.position)


@dataclass(frozen=True)
class ImdbEntry:
    tid: str
    title: str
    year: str
    director: str

    def __eq__(self, other):
        if not isinstance(other, ImdbEntry):
            return NotImplementedError
        return self.tid == other.tid

    def __hash__(self):
        return hash(self.tid)
