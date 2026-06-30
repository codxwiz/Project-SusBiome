"""
==============================================================
Risk Formatter Test
==============================================================

Tests the Risk Formatter.

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

from scripts.risk.formatter import (
    RiskFormatter,
)

print()
print("=" * 60)
print("RISK FORMATTER TEST")
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
# Build Risk Engine
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

df = CombinedRisk().build(
    df,
)

#
# Format
#

formatter = RiskFormatter()

formatted = formatter.format(
    df,
)

summary = formatter.summary(
    formatted,
)

print("Formatted Dataset")
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
    list(
        formatted.columns
    )
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

assert len(formatted) == 100

assert "overall_risk_score" in formatted.columns

assert "overall_risk_level" in formatted.columns

assert "dominant_hazard" in formatted.columns

assert summary["rows"] == 100

print()
print("=" * 60)
print("RISK FORMATTER PASSED")
print("=" * 60)