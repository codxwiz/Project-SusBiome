"""
==============================================================
Prediction Orchestrator Test
==============================================================

Tests the complete Prediction Pipeline.

Pipeline
--------
Training Dataset
        │
        ▼
Prediction Orchestrator
        │
        ▼
Inference
        │
        ▼
Formatter
        │
        ▼
Prediction Output
        │
        ▼
Summary

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.ml.models import (
    TRAINING_DATASET,
)

from scripts.prediction.orchestrator import (
    PredictionOrchestrator,
)

print()
print("=" * 60)
print("STARTING PREDICTION PIPELINE")
print("=" * 60)
print()

#
# Output file
#

OUTPUT = Path(
    "data/prediction/predictions.parquet"
)

#
# Create pipeline
#

pipeline = PredictionOrchestrator()

#
# Run prediction
#

predictions, summary = pipeline.run(

    input_path=TRAINING_DATASET,

    output_path=OUTPUT,

    include_probability=True,

)

print("Output")
print("-" * 20)
print()

print(
    OUTPUT
)

print()

print("Prediction Sample")
print("-" * 20)
print()

print(
    predictions.head()
)

print()

print("Summary")
print("-" * 20)
print()

for key, value in summary.items():

    print(
        f"{key:<20}: {value}"
    )

#
# Validation
#

assert OUTPUT.exists()

assert len(predictions) > 0

assert "flood_prediction" in predictions.columns

assert "drought_prediction" in predictions.columns

assert "cyclone_prediction" in predictions.columns

assert "flood_probability" in predictions.columns

assert "drought_probability" in predictions.columns

assert "cyclone_probability" in predictions.columns

#
# Reload saved file
#

saved = pd.read_parquet(
    OUTPUT,
)

assert len(saved) == len(predictions)

assert list(saved.columns) == list(predictions.columns)

print()

print("=" * 60)
print("PREDICTION PIPELINE PASSED")
print("=" * 60)