"""
==============================================================
Drought Risk Test
==============================================================

Tests the Drought Risk Engine.

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

from scripts.risk.drought import (
    DroughtRisk,
)

print()
print("=" * 60)
print("DROUGHT RISK TEST")
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
# Build Drought Risk
#

engine = DroughtRisk()

df = engine.build(
    df,
)

print(
    df[
        [
            "drought_prediction",
            "drought_probability",
            "drought_risk_score",
            "drought_risk_level",
        ]
    ].head()
)

print()

print("Distribution")
print("-" * 20)

print(
    df["drought_risk_level"]
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

assert "drought_risk_score" in df.columns

assert "drought_risk_level" in df.columns

assert len(df) == 100

print()
print("=" * 60)
print("DROUGHT RISK PASSED")
print("=" * 60)