import datetime
import re
from pathlib import Path

import streamlit as st
from st_keyup import st_keyup

LAST_UPDATE = datetime.date(2025, 8, 16)

st.set_page_config(
    page_title="Movie Journal",
    page_icon="🎥",  # optional emoji or path to an icon file
    layout="centered"  # or "wide"
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


@st.cache_data
def load_movies(path: Path):
    pat = re.compile(r"^(.*?)(?:\s*\(\s*([’']?\d{2,4})\s*\))?$")
    movies = []
    if not path.exists():
        return movies
    with path.open("r", encoding="utf-8-sig") as f:
        for num, ln in enumerate(ln.strip() for ln in f if ln.strip()):

            if '*' in ln:
                icon = '⭐'
            elif '✓' in ln:
                icon = '✅'
            elif '(bomb)' in ln:
                ln = ln.replace('(bomb)', '')
                icon = '💣'
            else:
                icon = None

            ln = ln.replace('*', '')
            ln = ln.replace('✓', '')
            ln = ln.strip()

            m = pat.match(ln)
            if m:
                title = m.group(1).strip()
                raw_year = (m.group(2) or "").replace("’", "'").strip()
                year = raw_year.lstrip("'") if raw_year else None
                movie = {"title": title, "year": year}
            else:
                movie = {"title": ln, "year": None}
            movie |= {'icon': icon, 'num': num + 1}
            movies.append(movie)
    return movies


path = Path("movie_journal.txt")
movies = load_movies(path)

st.title("🎬 Movie Journal")
st.write(f"You've seen **{len(movies)} movies!**")
st.caption(f"Last updated on {LAST_UPDATE.strftime('%B %-d, %Y')}")

if not movies:
    st.info("movie_journal.txt not found or empty.")
    st.stop()

# --- Live search (updates every keystroke) -----------------------------------
query = st_keyup(
    "Search",
    key="query",
    placeholder="Type to filter...",
) or ""
query = query.strip().lower()

mark_filter = st.radio(
    "Filter by mark", [
        "All",
        "✅",
        "⭐",
        "✅/⭐",
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


def matches_text(mv, q: str) -> bool:
    if not q:
        return True
    return (q in mv["title"].lower()
            ) or (mv["year"] and q in mv["year"].lower())


def matches_mark(mv) -> bool:
    if mark_filter == "All":
        return True
    if '✅' in mark_filter and '⭐' in mark_filter:
        return mv["icon"] in ("✅", "⭐")
    if mark_filter.startswith("⭐"):
        return mv["icon"] == "⭐"
    if mark_filter.startswith("💣"):
        return mv["icon"] == "💣"
    if mark_filter.startswith("✅"):
        return mv["icon"] == "✅"
    # "— None"
    return mv["icon"] is None


def matches(mv, q):
    if not q:
        return True
    return (q in mv["title"].lower()
            ) or (mv["year"] and q in mv["year"].lower())


# filtered = [m for m in movies if matches(m, query)]
filtered = [m for m in movies if matches_text(m, query) and matches_mark(m)]

# Apply order flipping
if flip_order:
    filtered = list(reversed(filtered))

# --- Compact grid render -----------------------------------------------------
for mv in filtered:
    num = mv['num']

    icon = mv['icon'] or ''

    # # Don't show icon when filtering by icon
    # if mark_filter not in ('All', None):
    #     icon = ''

    out = f"{num}. **{mv['title']}**"
    if mv["year"]:
        out += f" · *{mv['year']}*"
    else:
        out += ''

    st.markdown(out + f' &nbsp;{icon}')

st.markdown('')

# Status
st.caption(f"Showing {len(filtered)} of {len(movies)}")
