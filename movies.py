import datetime
import re
from collections import defaultdict
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from st_keyup import st_keyup

from linker import ImdbTidMapper, get_default_mapper
from models import ImdbEntry, JournalEntry
from parsers.log import parse_movie_log


def matches_text(mv: JournalEntry, q: str) -> bool:
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


def matches(mv: JournalEntry, q):
    if not q:
        return True
    return (q in mv.title.lower()
            ) or (mv.year is not None and q in mv.year.lower())


@st.cache_data
def load_movies():
    mapper = get_default_mapper()
    return mapper.load_journal()


def main():
    movies = load_movies()
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

    /* Disable URL colors and underline */
    a.no-style {
        color: inherit !important;
        text-decoration: none !important;
    }

    /* Underline hovered links */
    a.no-style:hover {
        text-decoration: underline !important;
    }
    </style>
    """,
        unsafe_allow_html=True
    )

    st.title("🎬 Movie Journal")
    st.markdown(
        f"You've seen **{len(movies)-num_duplicates} movies!**",
        help=(
            'Some films were logged twice or grouped (e.g., sequels and remakes).\n\n'
            'List numbers may not line up exactly, but the total count is accurate.'
        )
    )

    if not movies:
        st.info("Movie journal file not found or empty.")
        st.stop()

    tab_list, tab_table, tab_hist, tab_directors, tab_composers, tab_cleanup = st.tabs(
        [
            "List",
            "Table",
            "Histogram",
            "Directors",
            "Composers",
            "Clean-up",
        ]
    )

    with tab_list:
        render_tab_list(movies)

    with tab_table:
        render_tab_table(movies)

    with tab_hist:
        render_tab_hist(movies)

    with tab_directors:
        # render_director_pie_chart(movies)
        render_director_count_list(movies)

    with tab_composers:
        render_composer_counts(movies)

    with tab_cleanup:
        render_duplicates(duplicates)
        render_missing_tids(movies)


def render_tab_list(movies: list[JournalEntry]):
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
            "⭐ or ✅",
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

    render_journal_list(filtered)
    st.caption(f"Showing {len(filtered)} of {len(movies)}")


def render_journal_list(journal: list[JournalEntry]):
    '''Renders a list of journal entries'''

    for mv in journal:
        num = mv.position
        icon = mv.mark or ''

        # Escape asterisks from markdown
        out = f"**{mv.title.replace('*', '&#42;')}**"

        if mv.tid:
            out = f'<a class="no-style" href="https://www.imdb.com/title/{mv.tid}">{out}<a>'

        if mv.backfill is not None:
            out += ' <span title="This entry was backfilled (original position unknown)">↵</span> '

        if mv.year:
            if mv.backfill is None:
                out += " · "
            out += f"*{mv.year}*"

        st.markdown(
            f'{num}. ' + out + f' &nbsp;{icon}'.strip(),
            unsafe_allow_html=True,
        )


def render_tab_hist(movies: list[JournalEntry]):

    year_entries = []
    noyear_entries = []
    for m in movies:
        if m.year and m.year.isdigit():
            year_entries.append(m)
        else:
            noyear_entries.append(m)

    years = [int(m.year) for m in year_entries]

    if not years:
        st.info("No movies with year information.")
        return

    df = pd.DataFrame(years, columns=pd.Index(["Year"]))

    all_years = pd.DataFrame({"Year": range(min(years), max(years) + 1)})
    df_counts = df.value_counts().reset_index(name="Count")
    df_counts = (
        all_years.merge(df_counts, on="Year",
                        how="left").fillna(0).astype({"Count": int})
    )

    chart = (
        alt.Chart(df_counts).mark_bar().encode(
            x=alt.X("Year:O", sort="ascending", axis=alt.Axis(labelAngle=-45)),
            y="Count"
        )
    )

    st.altair_chart(chart, use_container_width=True)

    if noyear_entries:
        out = '\n\n'.join(f'- {m.title}' for m in noyear_entries)
        st.markdown(f'The following films are missing a year:\n\n{out}')


def render_tab_table(movies: list[JournalEntry]):
    df = pd.DataFrame(
        [
            e.__dict__ | {
                'director': None if e.imdb is None else e.imdb.director,
                'link':
                f'https://www.imdb.com/title/{e.tid}' if e.tid else None,
                'mark': e.mark or '',
                'composer': e.imdb.composer if e.imdb else '',
            } for e in movies
        ]
    )
    df_subset: pd.DataFrame = df.loc[:, [
        'position', 'title', 'year', 'director', 'composer', 'mark', 'link'
    ]]
    df_display = df_subset.rename(
        columns={
            "position": "Watch #",
            "year": "Release Year",
            "title": "Title",
            "mark": "Mark",
            "director": "Director",
            "link": "Link",
            "composer": "Composer",
        }
    )
    st.dataframe(
        df_display,
        hide_index=True,
        height=35 * 100,
        column_config={
            'Link': st.column_config.LinkColumn(display_text='IMDb')
        }
    )


def render_duplicates(duplicates: dict[str, list[JournalEntry]]):
    rows = []
    for (title, year), v in duplicates.items():
        if len(v) > 1:
            d = {"Title": title, "Year": year}
            d |= {(f'Pos #{i+1}'): e.position for i, e in enumerate(v)}
            rows.append(d)
    if rows:
        st.subheader('Duplicates')
        st.write(
            "These titles appear multiple times but are excluded from the final film count."
        )
        df = pd.DataFrame(rows)
        df = df.sort_values(by="Pos #2", na_position="last")
        df.index = df.index + 1
        st.dataframe(df, height=int(35.125 * (len(rows) + 1)))
    else:
        st.info("No duplicates found ✅")


def find_duplicates(movies: list[JournalEntry]):
    d = defaultdict(list)
    for m in movies:
        d[m.title, m.year].append(m)
    return {k: v for k, v in d.items() if len(v) > 1}


def render_missing_tids(movies: list[JournalEntry]):
    missing = [
        {
            'Title': m.title,
            'Year': m.year,
            'Position': m.position,
        } for m in movies if m.tid is None
    ]
    if missing:
        st.subheader('Titles Missing an IMDb ID')
        df = pd.DataFrame(missing)
        st.dataframe(df)


def count_directors(journal: list[JournalEntry]):
    '''Counts the frequency of directors in a list of journal entries.'''
    df = pd.DataFrame([e.imdb.__dict__ for e in journal if e.imdb])

    # Split directors on commas and expand into multiple rows
    directors = (df["director"].str.split(",").explode().str.strip())

    counts = directors.value_counts().reset_index()
    counts.columns = ["Director", "Count"]
    counts = counts.sort_values(
        by=["Count", "Director"], ascending=[False, True]
    )
    return counts


def count_composers(journal: list[JournalEntry]):
    composers = []
    for entry in journal:
        if entry.imdb and entry.imdb.composer:
            for comp in entry.imdb.composer.split(","):
                composers.append(comp.strip())

    df = pd.DataFrame(composers, columns=["Composer"])
    counts = df.value_counts().reset_index(name="Count")
    counts["Count"] = counts["Count"].astype(int)

    counts = counts.sort_values(
        ["Count", "Composer"], ascending=[False, True]
    ).reset_index(drop=True)
    counts.index = counts.index + 1
    counts = counts[["Count", "Composer"]]
    return counts


def render_composer_counts(journal: list[JournalEntry]):
    counts = count_composers(journal)
    counts = counts[['Count', 'Composer']]

    st.subheader('Films Seen Per Composer')

    event = st.dataframe(
        counts,
        # height=35 * 200,
        width=400,
        selection_mode="single-row",
        on_select="rerun",
    )

    if event and 'selection' in event:
        selected_directors = counts.iloc[event["selection"]["rows"]
                                         ]["Composer"].tolist()

        matches = [
            e for e in journal if e.imdb and any(
                d.strip() in selected_directors
                for d in e.imdb.composer.split(",")
            )
        ]

        matches.sort(key=lambda e: (e.imdb.year, e.imdb.title), reverse=True)

        lines = []

        for m in matches:
            title = f"**{m.title.replace('*', '&#42;')}**"

            if m.tid:
                title = f'<a class="no-style" href="https://www.imdb.com/title/{m.tid}">{title}<a>'

            lines.append(
                f"- {title} · *{m.imdb.year}* {m.mark or ''} – {m.imdb.composer}"
            )

        st.markdown(
            '\n'.join(lines) if lines else "_No matching entries._",
            unsafe_allow_html=True
        )


def render_director_pie_chart(journal: list[JournalEntry]):
    counts = count_directors(journal).copy()

    counts["DirectorLabel"] = counts.apply(
        lambda r: f"{r['Director']} ({r['Count']})", axis=1
    )

    chart = (
        alt.Chart(counts).mark_arc().encode(
            theta="Count",
            color=alt.Color(
                "DirectorLabel",
                sort=alt.SortField(field="Count", order="descending"),
                title="Director"
            ),
            tooltip=["Director", "Count"],
            order=alt.Order("Count", sort="descending"),
        )
    )

    st.altair_chart(chart, use_container_width=True)


def render_director_count_list(journal: list[JournalEntry]):
    counts = count_directors(journal)
    st.subheader('Films Seen Per Director')

    # # Ordered list
    # lines = '\n'.join(
    #     f'1. **{row.Director}** ({row.Count})'
    #     for row in counts.itertuples(index=False)
    # )
    # st.markdown(lines)

    # Data frame
    counts = counts[['Count', 'Director']]
    counts.index = counts.index + 1
    event = st.dataframe(
        counts,
        # height=35 * 200,
        width=400,
        selection_mode="single-row",
        on_select="rerun",
    )

    if event and 'selection' in event:
        selected_directors = counts.iloc[event["selection"]["rows"]
                                         ]["Director"].tolist()

        matches = [
            e for e in journal if e.imdb and any(
                d.strip() in selected_directors
                for d in e.imdb.director.split(",")
            )
        ]

        matches.sort(key=lambda e: (e.imdb.year, e.imdb.title), reverse=True)

        lines = []

        for m in matches:
            title = f"**{m.title.replace('*', '&#42;')}**"

            if m.tid:
                title = f'<a class="no-style" href="https://www.imdb.com/title/{m.tid}">{title}<a>'

            lines.append(
                f"- {title} · *{m.imdb.year}* {m.mark or ''} – {m.imdb.director}"
            )

        st.markdown(
            '\n'.join(lines) if lines else "_No matching entries._",
            unsafe_allow_html=True
        )


if __name__ == '__main__':
    main()
