"""
============================================================
Test Unified Dataset
============================================================
"""

from pathlib import Path

from scripts.fusion.dataset import UnifiedDataset


DATASET = Path(

    "data/fusion/unified.parquet"

)

df = UnifiedDataset.load(

    DATASET

)

UnifiedDataset.info(

    df

)

print()

print("=" * 60)

print("DATASET TEST PASSED")

print("=" * 60)