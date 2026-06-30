"""
==============================================================
Flood Risk Test
==============================================================

Tests the Flood Risk Engine.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import pandas as pd

from scripts.ml.models import (
    TRAINING_DATASET,
)

from scripts.prediction.inference import (
    PredictionInference,
)

from scripts.risk.flood import (
    FloodRisk,
)

print()
print("=" * 60)
print("FLOOD RISK TEST")
print("=" * 60)
print()

#
# Load dataset
#

df = pd.read_parquet(
    TRAINING_DATASET,
)

#
# Small sample
#

df = df.head(
    100,
)

#
# Generate predictions
#

predictor = PredictionInference()

df = predictor.predict(
    df,
)

#
# Build Flood Risk
#

engine = FloodRisk()

df = engine.build(
    df,
)

print(
    df[
        [
            "flood_prediction",
            "flood_probability",
            "flood_risk_score",
            "flood_risk_level",
        ]
    ].head()
)

print()

print("Distribution")
print("-" * 20)

print(
    df["flood_risk_level"]
    .value_counts()
)

summary = engine.summary(
    df,
)

print()

print(summary)

#
# Validation
#

assert "flood_risk_score" in df.columns

assert "flood_risk_level" in df.columns

assert len(df) == 100

print()
print("=" * 60)
print("FLOOD RISK PASSED")
print("=" * 60)