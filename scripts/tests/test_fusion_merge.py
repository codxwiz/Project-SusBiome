"""
============================================================
Test Fusion Merge
============================================================
"""

from pathlib import Path

from scripts.fusion.align import DataAligner
from scripts.fusion.merge import DatasetMerger


NASA = Path(
    "data/silver/gpm/G3365998689-GES_DISC.parquet"
)

ERA5 = Path(
    "data/silver/era5/reanalysis-era5-single-levels_2024_07.parquet"
)

aligner = DataAligner()

merger = DatasetMerger()

left = aligner.align(

    aligner.load(NASA)

)

right = aligner.align(

    aligner.load(ERA5)

)

merged = merger.run(

    left=left,

    right=right,

)

print()

print("=" * 60)
print("MERGED DATASET")
print("=" * 60)

print()

print(merged.head())

print()

print(f"Rows : {len(merged):,}")

print()

print("=" * 60)
print("MERGE PASSED")
print("=" * 60)