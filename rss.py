'''Generates an RSS feed of recently watched films.

Watch dates are approximated from git commit dates of each line in `movie_journal.txt` that introduced it
'''

import datetime
import os
import subprocess
from email.utils import format_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from models import JournalEntry

FEED_TITLE = '🎬 Movie Journal'
FEED_DESCRIPTION = 'Recently watched films, in viewing order.'
MAX_ITEMS = 50
SITE_URL = os.environ.get('FEED_SITE_URL', 'https://movies.xikkub.com')


def get_line_dates(path: Path) -> list[datetime.date]:
    '''Returns one date per raw line of `path`, taken from the git commit
    that last touched it (falls back to today if git/history is unavailable).'''
    try:
        out = subprocess.run(
            [
                'git', '-c', 'safe.directory=*', 'blame',
                '--line-porcelain', path.name,
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=path.parent,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        with open(path) as f:
            return [datetime.date.today() for _ in f]

    dates = []
    author_time = None
    for line in out.splitlines():
        if line.startswith('author-time '):
            author_time = int(line.split()[1])
        elif line.startswith('\t'):
            dates.append(datetime.date.fromtimestamp(author_time))
    return dates


def get_position_dates(path: Path) -> dict[int, datetime.date]:
    '''Maps each journal entry's 1-indexed position (as assigned by
    parse_movie_log, which skips blank lines) to the date it was added.'''
    with open(path) as f:
        raw_lines = f.readlines()

    line_dates = get_line_dates(path)

    non_blank_dates = [
        date for line, date in zip(raw_lines, line_dates) if line.strip()
    ]
    return dict(enumerate(non_blank_dates, start=1))


def generate_rss(
    journal: list[JournalEntry],
    dates: dict[int, datetime.date],
    site_url: str = SITE_URL,
) -> str:
    '''Builds an RSS 2.0 feed of the most recently watched films.'''

    ordered = sorted(
        journal, key=lambda e: (e.position, e.subnum), reverse=True
    )[:MAX_ITEMS]

    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = FEED_TITLE
    ET.SubElement(channel, 'link').text = site_url
    ET.SubElement(channel, 'description').text = FEED_DESCRIPTION
    ET.SubElement(channel, 'language').text = 'en-us'
    ET.SubElement(channel, 'lastBuildDate').text = format_datetime(
        datetime.datetime.now(datetime.timezone.utc)
    )

    for entry in ordered:
        item = ET.SubElement(channel, 'item')

        title = entry.title
        if entry.year:
            title += f' ({entry.year})'
        if entry.mark:
            title += f' {entry.mark}'
        ET.SubElement(item, 'title').text = title

        link = f'https://www.imdb.com/title/{entry.tid}' if entry.tid else site_url
        ET.SubElement(item, 'link').text = link

        guid = ET.SubElement(item, 'guid', isPermaLink='false')
        guid.text = f'movie-journal-{entry.position}-{entry.subnum}'

        entry_date = dates.get(entry.position, datetime.date.today())
        pub_dt = datetime.datetime(
            entry_date.year,
            entry_date.month,
            entry_date.day,
            tzinfo=datetime.timezone.utc,
        )
        ET.SubElement(item, 'pubDate').text = format_datetime(pub_dt)

        director = entry.imdb.director if entry.imdb else None
        description = f'Watch #{entry.position}'
        if director:
            description += f' · Directed by {director}'
        ET.SubElement(item, 'description').text = description

    ET.indent(rss)
    return ET.tostring(rss, encoding='unicode', xml_declaration=True)


def write_feed(
    journal: list[JournalEntry],
    journal_path: Path = Path('movie_journal.txt'),
    out_path: Path = Path('static/feed.xml'),
) -> None:
    dates = get_position_dates(journal_path)
    xml = generate_rss(journal, dates)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(xml)
