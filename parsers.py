import re

from models import LogEntry


def parse_single_entry(line: str, num: int, subnum: int):
    if '*' in line:
        icon = '⭐'
    elif '✓' in line:
        icon = '✅'
    elif '(bomb)' in line:
        line = line.replace('(bomb)', '')
        icon = '💣'
    else:
        icon = None

    line = line.replace('*', '')
    line = line.replace('✓', '')
    line = line.strip()

    pat = re.compile(r"^(.*?)(?:\s*\(\s*([’']?\d{2,4})\s*\))?$")
    m = pat.match(line)

    if m:
        title = m.group(1).strip()
        raw_year = (m.group(2) or "").replace("’", "'").strip()
        year = raw_year.lstrip("'") if raw_year else None
    else:
        title = line
        year = None

    return LogEntry(num, subnum, title, icon, year)


def parse_line_entries(line: str, num: int) -> list[LogEntry]:
    return [
        parse_single_entry(segment, num, i)
        for i, segment in enumerate(line.split(' :: '))
    ]


def parse_movie_log(path) -> list[LogEntry]:
    with open(path) as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    movies = []
    for num, ln in enumerate(lines, start=1):
        movies += parse_line_entries(ln, num)
    return movies
