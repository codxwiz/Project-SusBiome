"""
============================================================
Feature Engineering Orchestrator Test
============================================================
"""

from pathlib import Path

import pandas as pd

from scripts.features.orchestrator import (
    FeatureEngineeringOrchestrator,
)

INPUT = Path(
    "data/fusion/unified.parquet"
)

OUTPUT = Path(
    "data/gold/features.parquet"
)

print()
print("=" * 60)
print("STARTING FEATURE ENGINEERING")
print("=" * 60)

pipeline = FeatureEngineeringOrchestrator()

result = pipeline.run(

    input_path=INPUT,

    output_path=OUTPUT,

)

print()

print("Output")

print(result)

print()

df = pd.read_parquet(result)

print()

print("Rows :", len(df))

print()

print(df.head())

print()

print("=" * 60)
print("FEATURE ENGINEERING PASSED")
print("=" * 60)