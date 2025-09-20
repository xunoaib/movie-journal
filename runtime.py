import os
from pathlib import Path
from typing import Any

import pandas as pd

from linker import get_default_mapper

IMDB_DATA_DIR = Path('imdb-data')

mapper = get_default_mapper()
journal = mapper.load_journal()
journal_tids = {e.tid for e in journal}

df = pd.read_csv(
    IMDB_DATA_DIR / 'title.basics.tsv.gz',
    sep='\t',
    dtype=str,
    na_values='\\N'
)

df = df[df['tconst'].isin(journal_tids)]

df['runtimeMinutes'] = pd.to_numeric(df['runtimeMinutes'], errors='coerce')

df = df.dropna(subset=['runtimeMinutes'])

total_runtime = df['runtimeMinutes'].sum()

hours = total_runtime // 60
days = hours // 24

print(f'Total runtime: {total_runtime:,} minutes')
print(f'= ~{hours:,} hours (~{days:,} days)')
