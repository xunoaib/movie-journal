import datetime
import re
from collections import defaultdict
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from st_keyup import st_keyup

from models import LogEntry
from parsers import parse_movie_log


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

    duplicates = find_duplicates(movies)
    num_duplicates = sum(len(v) - 1 for v in duplicates.values())

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

    st.title("🎬 Movie Journal")
    st.markdown(
        f"You've seen **{len(movies)-num_duplicates} movies!**",
        help=(
            'Some sequels and remakes share a list number, so numbering may differ -- but the total count is accurate.'
        )
    )

    if not movies:
        st.info("movie_journal.txt not found or empty.")
        st.stop()

    tab_list, tab_hist, tab_table, tab_dupes = st.tabs(
        ["List", "Histogram", "Table", "Duplicates"]
    )

    with tab_list:
        render_tab_list(movies)

    with tab_hist:
        render_tab_hist(movies)

    with tab_table:
        render_tab_table(movies)

    with tab_dupes:
        duplicate_check(duplicates)


def render_tab_list(movies: list[LogEntry]):
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


def render_tab_hist(movies: list[LogEntry]):
    # Only include entries with a year
    year_entries = [m for m in movies if m.year and m.year.isdigit()]
    df = pd.DataFrame([int(m.year) for m in year_entries], columns=["Year"])
    df_counts = df.value_counts().reset_index(name="Count")

    chart = (
        alt.Chart(df_counts).mark_bar().encode(
            x=alt.X("Year:O", sort="ascending", axis=alt.Axis(labelAngle=-45)),
            y="Count"
        )
    )
    st.altair_chart(chart, use_container_width=True)


def render_tab_table(movies: list[LogEntry]):
    df = pd.DataFrame([e.__dict__ for e in movies])
    df_display = df[['position', 'title', 'year', 'mark']].rename(
        columns={
            "position": "Watch #",
            "year": "Release Year",
            "title": "Title",
            "mark": "Mark"
        }
    )
    st.dataframe(df_display, hide_index=True)


def duplicate_check(duplicates: dict[str, list[LogEntry]]):
    rows = []
    for (title, year), v in duplicates.items():
        if len(v) > 1:
            positions = ', '.join(str(e.position) for e in v)
            rows.append({"Title": title, "Year": year, "Positions": positions})

    if rows:
        df = pd.DataFrame(rows)
        # st.dataframe(df, hide_index=True)
        st.dataframe(df)
    else:
        st.info("No duplicates found ✅")


def find_duplicates(movies: list[LogEntry]):
    d = defaultdict(list)

    for m in movies:
        d[m.title, m.year].append(m)

    return {k: v for k, v in d.items() if len(v) > 1}


if __name__ == '__main__':
    main()
