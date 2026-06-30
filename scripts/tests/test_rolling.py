"""
============================================================
Rolling Feature Test
============================================================
"""

from pathlib import Path

import pandas as pd

from scripts.features.rolling import RollingFeatureEngineer


INPUT = Path(
    "data/fusion/unified.parquet"
)

print()
print("=" * 60)
print("ROLLING FEATURE TEST")
print("=" * 60)
print()

df = pd.read_parquet(INPUT)

engineer = RollingFeatureEngineer()

result = engineer.build(df)

columns = [

    "precipitation_7d_sum",
    "precipitation_30d_sum",
    "precipitation_90d_sum",

    "temperature_7d_mean",
    "temperature_30d_mean",
    "temperature_90d_mean",

]

print(result[columns].head())

print()
print("Rows :", len(result))

print()
print("=" * 60)
print("ROLLING FEATURES PASSED")
print("=" * 60)