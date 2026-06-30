"""
============================================================
Feature Engineering Test
============================================================
"""

from pathlib import Path

import pandas as pd

from scripts.features.engineering import FeatureEngineering


INPUT = Path(
    "data/fusion/unified.parquet"
)

print()
print("=" * 60)
print("FEATURE ENGINEERING TEST")
print("=" * 60)
print()

df = pd.read_parquet(INPUT)

engineer = FeatureEngineering()

result = engineer.build(df)

print(result.head())

print()

print("Columns")

print("-" * 60)

for column in result.columns:

    print(column)

print()

print("Rows :", len(result))

print()

print("=" * 60)
print("FEATURE ENGINEERING PASSED")
print("=" * 60)