"""
============================================================
Test Fusion Alignment
============================================================
"""

from pathlib import Path

import pandas as pd
from scripts.fusion.align import DataAligner


NASA = Path(
    "data/silver/gpm/G3365998689-GES_DISC.parquet"
)

ERA5 = Path(
    "data/silver/era5/reanalysis-era5-single-levels_2024_07.parquet"
)

aligner = DataAligner()

gpm = aligner.align(
    aligner.load(NASA)
)

era5 = aligner.align(
    aligner.load(ERA5)
)

print()
print("=" * 60)
print("ALIGNMENT TEST")
print("=" * 60)

print()
print("Longitude Ranges")
print("----------------")
print(
    "NASA :",
    gpm["longitude"].min(),
    "->",
    gpm["longitude"].max(),
)

print(
    "ERA5 :",
    era5["longitude"].min(),
    "->",
    era5["longitude"].max(),
)
print()
print("Latitude Ranges")
print("----------------")
print(
    "NASA :",
    gpm["latitude"].min(),
    "->",
    gpm["latitude"].max(),
)

print(
    "ERA5 :",
    era5["latitude"].min(),
    "->",
    era5["latitude"].max(),
)

print()

print("NASA")

print(gpm.head())

print()

print("ERA5")

print(era5.head())

print()

print("=" * 60)
print("ALIGNMENT PASSED")
print("=" * 60)