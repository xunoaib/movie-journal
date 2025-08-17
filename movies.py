import datetime
import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from st_keyup import st_keyup

from models import LogEntry

st.set_page_config(
    page_title="Movie Journal", page_icon="🎥", layout="centered"
)

st.markdown(
    """
<style>
ol {
    margin-top: 0.2rem;   /* reduce space above list */
    margin-bottom: 0.2rem;/* reduce space below list */
    padding-left: 1.2rem; /* keep indentation nice */
}
</style>
""",
    unsafe_allow_html=True
)


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


def matches_text(mv: LogEntry, q: str) -> bool:
    if not q:
        return True
    return (q in mv.title.lower()
            ) or (mv.year is not None and q in mv.year.lower())


def matches_mark(mv, mark_filter) -> bool:
    if mark_filter == "All":
        return True
    if '✅' in mark_filter and '⭐' in mark_filter:
        return mv.mark in ("✅", "⭐")
    if mark_filter.startswith("⭐"):
        return mv.mark == "⭐"
    if mark_filter.startswith("💣"):
        return mv.mark == "💣"
    if mark_filter.startswith("✅"):
        return mv.mark == "✅"
    return mv.mark is None


def matches(mv: LogEntry, q):
    if not q:
        return True
    return (q in mv.title.lower()
            ) or (mv.year is not None and q in mv.year.lower())


def main():
    path = Path("movie_journal.txt")
    movies = parse_movie_log(path)

    st.title("🎬 Movie Journal")
    st.markdown(
        f"You've seen **{len(movies)} movies!**",
        help=(
            'Some sequels and remakes share a list number, so numbering may differ -- but the total count is accurate.'
        )
    )

    if not movies:
        st.info("movie_journal.txt not found or empty.")
        st.stop()

    tab_list, tab_hist = st.tabs(["List", "Histogram"])

    with tab_list:
        query = st_keyup(
            "Search",
            key="query",
            placeholder="Type to filter...",
        ) or ""
        query = query.strip().lower()

        mark_filter = st.radio(
            "Filter by mark", [
                "All",
                "⭐",
                "✅",
                "⭐|✅",
                "💣",
                "No mark",
            ],
            horizontal=True,
            help='\n\n'.join(
                [
                    '⭐ Stars denote particularly exceptional films.',
                    '✅ Checks denote exceptional films.',
                    '💣 Bombs are dangerous. Run!!',
                ]
            )
        )

        flip_order = st.toggle("Newest first", value=True)

        filtered = [
            m for m in movies
            if matches_text(m, query) and matches_mark(m, mark_filter)
        ]

        if flip_order:
            filtered = list(reversed(filtered))

        for mv in filtered:
            num = mv.position
            icon = mv.mark or ''
            out = f"{num}. **{mv.title}**"
            if mv.year:
                out += f" · *{mv.year}*"
            st.markdown(out + f' &nbsp;{icon}')

        st.caption(f"Showing {len(filtered)} of {len(movies)}")

    with tab_hist:
        # Only include entries with a year
        year_entries = [m for m in movies if m.year and m.year.isdigit()]
        df = pd.DataFrame(
            [int(m.year) for m in year_entries], columns=["Year"]
        )
        df_counts = df.value_counts().reset_index(name="Count")

        chart = (
            alt.Chart(df_counts).mark_bar().encode(
                x=alt.X(
                    "Year:O", sort="ascending", axis=alt.Axis(labelAngle=-45)
                ),
                y="Count"
            )
        )
        st.altair_chart(chart, use_container_width=True)


if __name__ == '__main__':
    main()
