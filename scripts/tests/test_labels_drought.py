"""
============================================================
Drought Label Test
============================================================
"""

from pathlib import Path

import pandas as pd

from scripts.labels.drought import DroughtLabelEngineer


INPUT = Path(
    "data/gold/features.parquet"
)

print()
print("=" * 60)
print("DROUGHT LABEL TEST")
print("=" * 60)
print()

df = pd.read_parquet(INPUT)

engineer = DroughtLabelEngineer()

result = engineer.build(df)

print(

    result[

        [

            "consecutive_dry_days",

            "precipitation_anomaly",

            "temperature_anomaly",

            "drought_risk",

        ]

    ].head()

)

print()

print(

    "Drought Events :",

    result["drought_risk"].sum(),

)

print()

print("=" * 60)
print("DROUGHT LABEL PASSED")
print("=" * 60)