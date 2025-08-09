import re
from pathlib import Path

import streamlit as st

st.title("🎬 Movie Journal")

path = Path("movie_journal.txt")

# Read lines, keep non-empty
lines = []
if path.exists():
    with path.open("r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
else:
    st.info("movie_journal.txt not found.")
    st.stop()

# Parse "Title ('78)" or "Title (1978)" or just "Title"
pat = re.compile(r"^(.*?)(?:\s*\(\s*([’']?\d{2,4})\s*\))?$")

movies = []
for ln in lines:

    # ln = re.sub(r'[*✓]', '', ln)
    ln = ln.replace('*', '')

    m = pat.match(ln)
    if not m:
        movies.append({"title": ln, "year": None})
        continue
    title = m.group(1).strip()
    raw_year = (m.group(2) or "").strip()
    # Normalize curly apostrophe to straight
    raw_year = raw_year.replace("’", "'")
    # Keep as-is if ambiguous; just strip leading apostrophe
    year = raw_year.lstrip("'") if raw_year else None
    movies.append({"title": title, "year": year})

# Compact 3-column grid (tweak to 4 if you want even denser)
cols_per_row = 3
cols_per_row = 1
for i in range(0, len(movies), cols_per_row):
    row = movies[i:i + cols_per_row]
    cols = st.columns(cols_per_row)
    for col, mv in zip(cols, row):
        with col:
            # Single tight line per movie
            if mv["year"]:
                st.markdown(f"**{mv['title']}** · *{mv['year']}*")
            else:
                st.markdown(f"**{mv['title']}**")
