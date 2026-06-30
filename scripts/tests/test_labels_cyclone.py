"""
============================================================
Cyclone Label Test
============================================================
"""

from pathlib import Path

import pandas as pd

from scripts.labels.cyclone import CycloneLabelEngineer


INPUT = Path(
    "data/gold/features.parquet"
)

print()
print("=" * 60)
print("CYCLONE LABEL TEST")
print("=" * 60)
print()

df = pd.read_parquet(INPUT)

engineer = CycloneLabelEngineer()

result = engineer.build(df)

print(

    result[

        [

            "precipitation",

            "value",

            "cyclone_risk",

        ]

    ].head()

)

print()

print(

    "Cyclone Events :",

    result["cyclone_risk"].sum(),

)

print()

print("=" * 60)
print("CYCLONE LABEL PASSED")
print("=" * 60)