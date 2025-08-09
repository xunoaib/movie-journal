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
    with path.open("r", encoding="utf-8") as f:
        for ln in (ln.strip() for ln in f if ln.strip()):
            m = pat.match(ln)
            if m:
                title = m.group(1).strip()
                raw_year = (m.group(2) or "").replace("’", "'").strip()
                year = raw_year.lstrip("'") if raw_year else None
                movies.append({"title": title, "year": year})
            else:
                movies.append({"title": ln, "year": None})
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
cols_per_row = 4
for i in range(0, len(filtered), cols_per_row):
    row = filtered[i:i + cols_per_row]
    cols = st.columns(cols_per_row)
    for col, mv in zip(cols, row):
        with col:
            if mv["year"]:
                st.markdown(f"**{mv['title']}** · *{mv['year']}*")
            else:
                st.markdown(f"**{mv['title']}**")

# Status
st.caption(f"Showing {len(filtered)} of {len(movies)}")
