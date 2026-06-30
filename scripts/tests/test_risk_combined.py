"""
==============================================================
Combined Risk Test
==============================================================

Tests the Combined Risk Engine.

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

from scripts.risk.combined import (
    CombinedRisk,
)

from scripts.risk.cyclone import (
    CycloneRisk,
)

from scripts.risk.drought import (
    DroughtRisk,
)

from scripts.risk.flood import (
    FloodRisk,
)

print()
print("=" * 60)
print("COMBINED RISK TEST")
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
# Individual risks
#

df = FloodRisk().build(
    df,
)

df = DroughtRisk().build(
    df,
)

df = CycloneRisk().build(
    df,
)

#
# Combined risk
#

engine = CombinedRisk()

df = engine.build(
    df,
)

print(
    df[
        [
            "flood_risk_level",
            "drought_risk_level",
            "cyclone_risk_level",
            "overall_risk_level",
            "dominant_hazard",
        ]
    ].head()
)

print()

print("Overall Risk Distribution")
print("-" * 30)

print()

print(
    df[
        "overall_risk_level"
    ]
    .value_counts()
)

print()

print("Dominant Hazard Distribution")
print("-" * 30)

print()

print(
    df[
        "dominant_hazard"
    ]
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

assert "overall_risk_score" in df.columns

assert "overall_risk_level" in df.columns

assert "dominant_hazard" in df.columns

assert len(df) == 100

print()
print("=" * 60)
print("COMBINED RISK PASSED")
print("=" * 60)