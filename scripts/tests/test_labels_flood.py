"""
============================================================
Flood Label Test
============================================================
"""

from pathlib import Path

import pandas as pd

from scripts.labels.flood import FloodLabelEngineer


INPUT = Path(
    "data/gold/features.parquet"
)

print()
print("=" * 60)
print("FLOOD LABEL TEST")
print("=" * 60)
print()

df = pd.read_parquet(INPUT)

engineer = FloodLabelEngineer()

result = engineer.build(df)

print(

    result[

        [

            "precipitation",

            "precipitation_7d_sum",

            "consecutive_wet_days",

            "flood_risk",

        ]

    ].head()

)

print()

print(

    "Flood Events :",

    result["flood_risk"].sum(),

)

print()

print("=" * 60)
print("FLOOD LABEL PASSED")
print("=" * 60)