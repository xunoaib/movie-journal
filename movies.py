import re
from pathlib import Path

import streamlit as st
from st_keyup import st_keyup

st.title("🎬 Movie Journal")


@st.cache_data
def load_movies(path: Path):
    pat = re.compile(r"^(.*?)(?:\s*\(\s*([’']?\d{2,4})\s*\))?$")
    movies = []
    if not path.exists():
        return movies
    with path.open("r", encoding="utf-8-sig") as f:
        for num, ln in enumerate(ln.strip() for ln in f if ln.strip()):

            if '*' in ln:
                mark = 'star'
            elif '✓' in ln:
                mark = 'check'
            else:
                mark = None

            ln = ln.replace('*', '')
            ln = ln.replace('✓', '')

            m = pat.match(ln)
            if m:
                title = m.group(1).strip()
                raw_year = (m.group(2) or "").replace("’", "'").strip()
                year = raw_year.lstrip("'") if raw_year else None
                movie = {"title": title, "year": year}
            else:
                movie = {"title": ln, "year": None}
            movie |= {'mark': mark, 'num': num + 1}
            movies.append(movie)
    return movies


path = Path("movie_journal.txt")
movies = load_movies(path)

if not movies:
    st.info("movie_journal.txt not found or empty.")
    st.stop()

# --- Live search (updates every keystroke) -----------------------------------
query = st_keyup(
    "Search",
    key="query",
    placeholder="Type to filter…",
) or ""
query = query.strip().lower()


def matches(mv, q):
    if not q:
        return True
    return (q in mv["title"].lower()
            ) or (mv["year"] and q in mv["year"].lower())


filtered = [m for m in movies if matches(m, query)]

# --- Compact grid render -----------------------------------------------------
cols_per_row = 1
for i in range(0, len(filtered), cols_per_row):
    row = filtered[i:i + cols_per_row]
    cols = st.columns(cols_per_row)
    for col, mv in zip(cols, row):
        with col:
            num = mv['num']
            if mv["year"]:
                st.markdown(f"{num}. **{mv['title']}** · *{mv['year']}*")
            else:
                st.markdown(f"{num}. **{mv['title']}**")

# Status
st.caption(f"Showing {len(filtered)} of {len(movies)}")
