"""
==============================================================
Cyclone Risk Test
==============================================================

Tests the Cyclone Risk Engine.

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

from scripts.risk.cyclone import (
    CycloneRisk,
)

print()
print("=" * 60)
print("CYCLONE RISK TEST")
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
# Build Cyclone Risk
#

engine = CycloneRisk()

df = engine.build(
    df,
)

print(
    df[
        [
            "cyclone_prediction",
            "cyclone_probability",
            "cyclone_risk_score",
            "cyclone_risk_level",
        ]
    ].head()
)

print()

print("Distribution")
print("-" * 20)

print(
    df["cyclone_risk_level"]
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

assert "cyclone_risk_score" in df.columns

assert "cyclone_risk_level" in df.columns

assert len(df) == 100

print()
print("=" * 60)
print("CYCLONE RISK PASSED")
print("=" * 60)