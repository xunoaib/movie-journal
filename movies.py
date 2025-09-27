import datetime
import pickle
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from st_keyup import st_keyup

from actors import (group_actors_by_journal, group_actors_by_journal_cached,
                    parse_proto_actors)
from linker import ImdbTidMapper, get_default_mapper
from models import ImdbEntry, JournalEntry, ProtoActor
from parsers.log import parse_movie_log


def matches_text(m: JournalEntry, q: str) -> bool:
    if not q:
        return True
    return q in m.title.lower() or (m.year is not None and q in m.year.lower())


def matches_mark(m: JournalEntry, mark_filter) -> bool:
    if mark_filter == "All":
        return True
    if '✅' in mark_filter and '⭐' in mark_filter:
        return m.mark in ("✅", "⭐")
    if mark_filter.startswith("⭐"):
        return m.mark == "⭐"
    if mark_filter.startswith("💣"):
        return m.mark == "💣"
    if mark_filter.startswith("✅"):
        return m.mark == "✅"
    return m.mark is None


def matches(mv: JournalEntry, q):
    if not q:
        return True
    return (q in mv.title.lower()
            ) or (mv.year is not None and q in mv.year.lower())


@dataclass
class Cache:
    journal: list[JournalEntry]
    proto_actors: list[ProtoActor]
    actors_by_journal: dict[str, list[ProtoActor]]


@st.cache_resource
def load_cache():
    print('Loading journal...', flush=True)
    journal = get_default_mapper().load_journal()

    print('Loading proto actors...', flush=True)
    tids = {j.tid or (j.imdb.tid if j.imdb else None)
            for j in journal} - {None}
    proto_actors = parse_proto_actors(tids)

    print('Grouping actors by journal...', flush=True)
    actors_by_journal = group_actors_by_journal(proto_actors, journal)

    print('Loaded!', flush=True)
    return Cache(journal, proto_actors, actors_by_journal)


def main():
    cache = load_cache()
    movies = cache.journal

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
        f"Total films: **{len(movies)-num_duplicates}**",
        help=(
            'Some films were logged twice or grouped (e.g., sequels and remakes).\n\n'
            'List numbers may not line up exactly, but the total count is accurate.'
        )
    )

    if not movies:
        st.info("Movie journal file not found or empty.")
        st.stop()

    tab_list, tab_table, tab_hist, tab_actors, tab_directors, tab_composers, tab_cleanup = st.tabs(
        [
            "List",
            "Table",
            "Histogram",
            "Actors",
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
        render_tab_histogram(movies)

    with tab_actors:
        render_tab_actors(movies, cache.actors_by_journal, cache.proto_actors)

    with tab_directors:
        render_tab_directors(movies)

    with tab_composers:
        render_tab_composers(movies)

    with tab_cleanup:
        render_duplicates(duplicates)
        render_missing_tids(movies)


def create_mark_filter(key: str | None = None, on_change=None):
    return st.radio(
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
        ),
        on_change=on_change,
        key=key
    )


def sync_filter_from_table():
    st.session_state["markFilterList"] = st.session_state["markFilterTable"]


def sync_filter_from_list():
    st.session_state["markFilterTable"] = st.session_state["markFilterList"]


def render_tab_list(movies: list[JournalEntry]):

    mark_filter = create_mark_filter(
        'markFilterList', on_change=sync_filter_from_list
    )
    st.session_state.markFilter = st.session_state["markFilterList"]

    query = st_keyup(
        "Search",
        key="query",
        placeholder="Type to filter...",
    ) or ""
    query = query.lower()

    filtered = [
        m for m in movies
        if matches_text(m, query) and matches_mark(m, mark_filter)
    ]

    flip_order = st.toggle("Newest first", value=True)
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


def render_tab_histogram(movies: list[JournalEntry]):
    year_entries = []
    noyear_entries = []
    for m in movies:
        if m.year and m.year.isdigit():
            year_entries.append(m)
        else:
            noyear_entries.append(m)

    if not year_entries:
        st.info("No movies with year information.")
        return

    years = [int(m.year) for m in year_entries]
    df_years = pd.DataFrame(years, columns=["Year"])
    all_years = pd.DataFrame({"Year": range(min(years), max(years) + 1)})

    df_counts = df_years.value_counts().reset_index(name="Count")
    df_counts = (
        all_years.merge(df_counts, on="Year",
                        how="left").fillna(0).astype({"Count": int})
    )

    chart_total = (
        alt.Chart(df_counts).mark_bar().encode(
            x=alt.X("Year:O", sort="ascending", axis=alt.Axis(labelAngle=-45)),
            y="Count"
        )
    )

    st.subheader("Number of Films by Release Date")
    st.altair_chart(chart_total, use_container_width=True)

    df_marks = pd.DataFrame(
        [(int(m.year), m.mark) for m in year_entries],
        columns=["Year", "Mark"]
    )

    counts = (
        df_marks.value_counts(["Year", "Mark"]).reset_index(name="Count")
    )

    counts = (
        all_years.merge(counts, on="Year",
                        how="left").fillna({
                            "Mark": "None",
                            "Count": 0
                        })
    )
    counts["Count"] = counts["Count"].astype(int)

    color_scale = alt.Scale(
        domain=["⭐", "✅", "💣"],
        range=["#ffcc00", "lightgreen", "red"],
    )

    chart_marked = (
        alt.Chart(counts).mark_bar().encode(
            x=alt.X("Year:O", sort="ascending", axis=alt.Axis(labelAngle=-45)),
            y="Count",
            color=alt.Color(
                "Mark",
                legend=alt.Legend(orient="bottom", direction="horizontal"),
                # legend=alt.Legend(title="Mark"),
                # legend=None,
                scale=color_scale,
            )
        )
    )

    st.subheader("Number of Marked Films by Release Date")

    st.altair_chart(chart_marked, use_container_width=True)

    if noyear_entries:
        out = "\n\n".join(f"- {m.title}" for m in noyear_entries)
        st.markdown(f"The following films are missing a year:\n\n{out}")


def render_tab_table(movies: list[JournalEntry]):

    mark_filter = create_mark_filter(
        'markFilterTable', on_change=sync_filter_from_table
    )
    st.session_state.markFilter = st.session_state["markFilterTable"]

    movies = [m for m in movies if matches_mark(m, mark_filter)]

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
    ]].sort_values(by='position', ascending=False)
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
        height=min(35 * 100, 35 * (len(df_display) + 1)),
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


def count_actors(
    journal: list[JournalEntry],
    actors_by_journal: dict[str, list[ProtoActor]],
    proto_actors: list[ProtoActor],
):
    actor_films = defaultdict(set)
    for tid, actors in actors_by_journal.items():
        for actor in actors:
            actor_films[actor.nconst].add(tid)

    tid_to_journal = {j.tid: j for j in journal}
    nconst_to_name = {a.nconst: a.name for a in proto_actors}

    star_tids = {j.tid for j in journal if j.starred}
    check_tids = {j.tid for j in journal if j.checked}

    df = pd.DataFrame(
        [
            {
                "Film Count": len(tids),
                "Actor": nconst_to_name[nconst],
                "⭐ Stars": len(star_tids & tids),
                "✅ Checks": len(check_tids & tids),
                "⭐✅ Total": len((star_tids | check_tids) & tids),
            } for nconst, tids in actor_films.items()
        ]
    ).sort_values("Film Count", ascending=False)

    df = df.sort_values(["Film Count", "Actor"],
                        ascending=[False, True]).reset_index(drop=True)

    df.index = df.index + 1
    return df


def count_directors(journal: list[JournalEntry]):
    '''Counts the frequency of directors in a list of journal entries.'''
    rows = []
    for entry in journal:
        if entry.imdb and entry.imdb.director:
            for names in entry.imdb.director.split(","):
                names = names.strip()
                rows.append({"Director": names, "Mark": entry.mark or ""})

    df = pd.DataFrame(rows)

    counts = (
        df.groupby("Director").agg(
            Count=("Director", "size"),
            Stars=("Mark", lambda m: (m == "⭐").sum()),
            Checks=("Mark", lambda m: (m == "✅").sum()),
            StarsAndChecks=("Mark", lambda m: ((m == "✅") | (m == "⭐")).sum()),
        ).reset_index()
    )

    counts = counts.sort_values(
        ["Count", "Director"], ascending=[False, True]
    ).reset_index(drop=True)

    counts.index = counts.index + 1

    return counts


def count_composers(journal: list[JournalEntry]):
    rows = []
    for entry in journal:
        if entry.imdb and entry.imdb.composer:
            for comp in entry.imdb.composer.split(","):
                comp = comp.strip()
                rows.append({"Composer": comp, "Mark": entry.mark or ""})

    df = pd.DataFrame(rows)

    counts = (
        df.groupby("Composer").agg(
            Count=("Composer", "size"),
            Stars=("Mark", lambda m: (m == "⭐").sum()),
            Checks=("Mark", lambda m: (m == "✅").sum()),
            StarsAndChecks=("Mark", lambda m: ((m == "✅") | (m == "⭐")).sum()),
        ).reset_index()
    )

    counts = counts.sort_values(
        ["Count", "Composer"], ascending=[False, True]
    ).reset_index(drop=True)

    counts.index = counts.index + 1

    return counts


def render_tab_composers(journal: list[JournalEntry]):
    counts = count_composers(journal)
    counts = counts[['Count', 'Composer', 'Stars', 'Checks', 'StarsAndChecks']]

    counts = counts.rename(columns={"Stars": "⭐ Stars"})
    counts = counts.rename(columns={"Checks": "✅ Checks"})
    counts = counts.rename(columns={"StarsAndChecks": "⭐✅ Total"})

    st.subheader(
        'Films Seen Per Composer',
        help='Click a checkbox to filter by composer!'
    )

    event = st.dataframe(
        counts,
        width=600,
        height=35 * 20,
        selection_mode="single-row",
        on_select="rerun",
    )

    if event and 'selection' in event:
        selected_composers = counts.iloc[event["selection"]["rows"]
                                         ]["Composer"].tolist()

        matches = [
            e for e in journal if e.imdb and any(
                c.strip() in selected_composers
                for c in e.imdb.composer.split(",")
            )
        ]

        matches.sort(key=lambda e: (e.imdb.year, e.imdb.title), reverse=True)

        lines = []
        for m in matches:
            title = f"**{m.title.replace('*', '&#42;')}**"
            if m.tid:
                title = f'<a class="no-style" href="https://www.imdb.com/title/{m.tid}">{title}<a>'
            composer = f' – {m.imdb.composer}' if ',' in m.imdb.composer else ''
            lines.append(
                f"- {title} · *{m.imdb.year}* {m.mark or ''}{composer}"
            )

        if selected_composers:
            st.subheader(', '.join(selected_composers))

        st.markdown(
            '\n'.join(lines)
            if lines else "_Click a checkbox to show matching films._",
            unsafe_allow_html=True
        )


def render_tab_actors(
    journal: list[JournalEntry],
    actors_by_journal: dict[str, list[ProtoActor]],
    proto_actors: list[ProtoActor],
):
    st.subheader(
        'Films Seen Per Actor',
        help='Click a checkbox to filter by actor!',
    )

    df = count_actors(journal, actors_by_journal, proto_actors)

    event = st.dataframe(
        df,
        use_container_width=False,
        width=600,
        height=35 * 20,
        # hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
    )

    if event and 'selection' in event:
        event_filter_actors(
            journal, actors_by_journal, proto_actors, df, event
        )


def event_filter_actors(
    journal: list[JournalEntry],
    actors_by_journal: dict[str, list[ProtoActor]],
    proto_actors: list[ProtoActor],
    df: pd.DataFrame,
    event,
):
    actor_names = df.iloc[event["selection"]["rows"]]["Actor"].to_list()
    actor_name = actor_names[0] if actor_names else object()
    match_protos = [a for a in proto_actors if a.name == actor_name]
    assert len(match_protos) <= 1, f'Multiple actor names: {match_protos}'

    match_proto_tids = match_protos[0].tids if match_protos else []
    matches = [j for j in journal if j.imdb and j.tid in match_proto_tids]
    matches.sort(key=lambda e: (e.imdb.year, e.imdb.title), reverse=True)

    lines = []

    for m in matches:
        title = f"**{m.title.replace('*', '&#42;')}**"

        if m.tid:
            title = f'<a class="no-style" href="https://www.imdb.com/title/{m.tid}">{title}<a>'

        lines.append(f"- {title} · *{m.imdb.year}* {m.mark or ''}")

    if actor_names:
        st.subheader(', '.join(actor_names))

    st.markdown(
        '\n'.join(lines)
        if lines else "_Click a checkbox to show matching films._",
        unsafe_allow_html=True
    )


def render_tab_directors(journal: list[JournalEntry]):
    counts = count_directors(journal)
    counts = counts[['Count', 'Director', 'Stars', 'Checks', 'StarsAndChecks']]

    counts = counts.rename(columns={"Stars": "⭐ Stars"})
    counts = counts.rename(columns={"Checks": "✅ Checks"})
    counts = counts.rename(columns={"StarsAndChecks": "⭐✅ Total"})

    st.subheader(
        'Films Seen Per Director',
        help='Click a checkbox to filter by director!'
    )

    event = st.dataframe(
        counts,
        width=600,
        height=35 * 20,
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

            director = f' – {m.imdb.director}' if ',' in m.imdb.director else ''

            lines.append(
                f"- {title} · *{m.imdb.year}* {m.mark or ''}{director}"
            )

        if selected_directors:
            st.subheader(', '.join(selected_directors))

        st.markdown(
            '\n'.join(lines)
            if lines else "_Click a checkbox to show matching films._",
            unsafe_allow_html=True
        )


if __name__ == '__main__':
    main()
