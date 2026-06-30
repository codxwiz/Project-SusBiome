"""
==============================================================
Prediction Inference Test
==============================================================

Tests the Prediction Inference Engine.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import pandas as pd

from scripts.prediction.inference import (
    PredictionInference,
)
from scripts.ml.models import (
    TRAINING_DATASET,
)

print()
print("=" * 60)
print("PREDICTION INFERENCE TEST")
print("=" * 60)
print()

#
# Load sample dataset
#

dataframe = pd.read_parquet(
    TRAINING_DATASET,
)

#
# Small sample keeps inference fast
#

dataframe = dataframe.head(
    100,
)

#
# Run inference
#

engine = PredictionInference()

result = engine.predict(
    dataframe,
)

print("Prediction Sample")
print("-" * 20)
print()

print(
    result[
        [
            "longitude",
            "latitude",
            "valid_time",
            "flood_prediction",
            "drought_prediction",
            "cyclone_prediction",
        ]
    ].head()
)

print()

print("Prediction Counts")
print("-" * 20)

print()

print(
    result["flood_prediction"]
    .value_counts()
    .sort_index()
)

print()

print(
    result["drought_prediction"]
    .value_counts()
    .sort_index()
)

print()

print(
    result["cyclone_prediction"]
    .value_counts()
    .sort_index()
)

#
# Validation
#

assert len(result) == len(dataframe)

assert "flood_prediction" in result.columns

assert "drought_prediction" in result.columns

assert "cyclone_prediction" in result.columns

assert "flood_probability" in result.columns

assert "drought_probability" in result.columns

assert "cyclone_probability" in result.columns

print()

print("=" * 60)
print("PREDICTION INFERENCE PASSED")
print("=" * 60)