"""
==============================================================
Prediction Formatter Test
==============================================================

Tests the Prediction Formatter.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import pandas as pd

from scripts.ml.models import (
    TRAINING_DATASET,
)

from scripts.prediction.formatter import (
    PredictionFormatter,
)

from scripts.prediction.inference import (
    PredictionInference,
)

print()
print("=" * 60)
print("PREDICTION FORMATTER TEST")
print("=" * 60)
print()

#
# Load sample dataset
#

dataframe = pd.read_parquet(
    TRAINING_DATASET,
)

#
# Small sample
#

dataframe = dataframe.head(
    100,
)

#
# Generate predictions
#

inference = PredictionInference()

predictions = inference.predict(
    dataframe,
)

#
# Format predictions
#

formatter = PredictionFormatter()

formatted = formatter.format(
    predictions,
)

summary = formatter.summary(
    formatted,
)

#
# Display
#

print("Formatted Prediction Sample")
print("-" * 30)
print()

print(
    formatted.head()
)

print()

print("Columns")
print("-" * 30)
print()

print(
    list(formatted.columns)
)

print()

print("Summary")
print("-" * 30)
print()

for key, value in summary.items():

    print(
        f"{key:<20}: {value}"
    )

#
# Validation
#

assert len(formatted) == len(predictions)

assert "longitude" in formatted.columns

assert "latitude" in formatted.columns

assert "valid_time" in formatted.columns

assert "flood_prediction" in formatted.columns

assert "drought_prediction" in formatted.columns

assert "cyclone_prediction" in formatted.columns

assert "flood_probability" in formatted.columns

assert "drought_probability" in formatted.columns

assert "cyclone_probability" in formatted.columns

assert summary["rows"] == len(formatted)

assert summary["flood_positive"] >= 0

assert summary["drought_positive"] >= 0

assert summary["cyclone_positive"] >= 0

print()

print("=" * 60)
print("PREDICTION FORMATTER PASSED")
print("=" * 60)