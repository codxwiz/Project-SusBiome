"""
============================================================
Test Fusion Orchestrator
============================================================
"""

from pathlib import Path

from scripts.fusion.orchestrator import FusionOrchestrator


NASA = Path(
    "data/silver/gpm/G3365998689-GES_DISC.parquet"
)

ERA5 = Path(
    "data/silver/era5/reanalysis-era5-single-levels_2024_07.parquet"
)

OUTPUT = Path(
    "data/fusion/unified.parquet"
)

fusion = FusionOrchestrator()

print()

print("=" * 60)

print("STARTING FUSION")

print("=" * 60)

result = fusion.run(

    left_path=NASA,

    right_path=ERA5,

    output_path=OUTPUT,

)

print()

print("Output")

print(result)

print()

print("=" * 60)

print("FUSION PASSED")

print("=" * 60)