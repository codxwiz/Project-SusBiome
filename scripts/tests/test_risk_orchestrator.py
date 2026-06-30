"""
==============================================================
Risk Orchestrator Test
==============================================================

Tests the complete Risk Engine pipeline.

Pipeline
--------
Prediction Dataset
        │
        ▼
Risk Orchestrator
        │
        ▼
Flood Risk
        │
        ▼
Drought Risk
        │
        ▼
Cyclone Risk
        │
        ▼
Combined Risk
        │
        ▼
Formatter
        │
        ▼
Risk Dataset

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.prediction.orchestrator import (
    PredictionOrchestrator,
)

from scripts.risk.orchestrator import (
    RiskOrchestrator,
)

print()
print("=" * 60)
print("STARTING RISK ENGINE")
print("=" * 60)
print()

#
# Input / Output
#

PREDICTION_OUTPUT = Path(
    "data/prediction/predictions.parquet"
)

RISK_OUTPUT = Path(
    "data/risk/risk.parquet"
)

#
# Ensure prediction dataset exists
#

prediction = PredictionOrchestrator()

prediction.run(

    input_path="data/gold/training.parquet",

    output_path=PREDICTION_OUTPUT,

)

#
# Risk Engine
#

pipeline = RiskOrchestrator()

risk, summary = pipeline.run(

    input_path=PREDICTION_OUTPUT,

    output_path=RISK_OUTPUT,

)

print("Output")
print("-" * 20)
print()

print(
    RISK_OUTPUT
)

print()

print("Risk Sample")
print("-" * 20)
print()

print(
    risk.head()
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

assert RISK_OUTPUT.exists()

assert len(risk) > 0

assert "flood_risk_score" in risk.columns

assert "drought_risk_score" in risk.columns

assert "cyclone_risk_score" in risk.columns

assert "overall_risk_score" in risk.columns

assert "overall_risk_level" in risk.columns

assert "dominant_hazard" in risk.columns

#
# Reload saved dataset
#

saved = pd.read_parquet(
    RISK_OUTPUT,
)

assert len(saved) == len(risk)

assert list(saved.columns) == list(risk.columns)

print()

print("=" * 60)
print("RISK ENGINE PASSED")
print("=" * 60)