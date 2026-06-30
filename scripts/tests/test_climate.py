"""
============================================================
Climate Feature Test
============================================================
"""

from pathlib import Path

import pandas as pd

from scripts.features.climate import ClimateFeatureEngineer


INPUT = Path(
    "data/fusion/unified.parquet"
)

print()
print("=" * 60)
print("CLIMATE FEATURE TEST")
print("=" * 60)
print()

df = pd.read_parquet(INPUT)

engineer = ClimateFeatureEngineer()

result = engineer.build(df)

columns = [

    "temperature_anomaly",

    "precipitation_anomaly",

    "consecutive_dry_days",

    "consecutive_wet_days",

    "rainfall_intensity",

    "hot_day",

    "cold_day",

]

print(result[columns].head())

print()
print("Rows :", len(result))

print()
print("=" * 60)
print("CLIMATE FEATURES PASSED")
print("=" * 60)