"""
============================================================
Label Engineering Test
============================================================
"""

from pathlib import Path

import pandas as pd

from scripts.labels.engineering import LabelEngineering


INPUT = Path(
    "data/gold/features.parquet"
)

print()
print("=" * 60)
print("LABEL ENGINEERING TEST")
print("=" * 60)
print()

df = pd.read_parquet(INPUT)

pipeline = LabelEngineering()

result = pipeline.build(df)

print(result.head())

print()

print(result.columns.tolist())

print()

print("=" * 60)
print("LABEL ENGINEERING PASSED")
print("=" * 60)