import re

from models import LogEntry


def parse_and_remove_mark(line: str):
    if '*' in line:
        icon = '⭐'
    elif '✓' in line:
        icon = '✅'
    elif '(bomb)' in line:
        icon = '💣'
    else:
        icon = None

    for s in ['(bomb)', ' *', '✓']:
        line = line.replace(s, ' ')

    line = re.sub(r'\s+', ' ', line)

    return icon, line.strip()


def parse_and_remove_tid(line: str):
    '''Find and remove tid in the form: [tt...] '''

    pattern = r'\[(tt.*?)\]'
    if m := re.search(pattern, line):
        tid = m.group(1)
        line = re.sub(pattern, '', line)
        line = re.sub(r'\s+', ' ', line).strip()
        return tid, line
    return None, line


def parse_and_remove_backfill(line: str):
    '''Find and remove backfill in the form: [bf:...]'''

    pattern = r'\[bf:(.*?)\]'
    if m := re.search(pattern, line):
        backfill = m.group(1).strip()
        line = re.sub(pattern, '', line)
        return backfill, line
    return None, line


def parse_single_entry(line: str, num: int, subnum: int):
    icon, line = parse_and_remove_mark(line)
    tid, line = parse_and_remove_tid(line)
    backfill, line = parse_and_remove_backfill(line)

    pat = re.compile(r"^(.*?)(?:\s*\(\s*([’']?\d{2,4})\s*\))?$")
    m = pat.match(line)

    if m:
        title = m.group(1).strip()
        raw_year = (m.group(2) or "").replace("’", "'").strip()
        year = raw_year.lstrip("'") if raw_year else None
    else:
        title = line
        year = None

    return LogEntry(num, subnum, title, icon, year, tid)


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
