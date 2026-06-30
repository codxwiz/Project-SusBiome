"""
==============================================================
Project SusBiome
Risk Engine Models
==============================================================

Shared constants, thresholds and data models for the
Risk Engine.

Responsibilities
----------------
• Risk level definitions
• Risk score mappings
• Prediction schema
• Output schema
• Validation constants
• Dataclasses

This module intentionally contains NO business logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


# ==========================================================
# INPUT COLUMNS
# ==========================================================

METADATA_COLUMNS = [

    "longitude",

    "latitude",

    "valid_time",

]


PREDICTION_COLUMNS = [

    "flood_prediction",

    "drought_prediction",

    "cyclone_prediction",

]


PROBABILITY_COLUMNS = [

    "flood_probability",

    "drought_probability",

    "cyclone_probability",

]


REQUIRED_COLUMNS = (
    METADATA_COLUMNS
    + ["flood_prediction", "cyclone_prediction"]
    + ["flood_probability", "cyclone_probability"]
)


def validate_prediction_values(dataframe: pd.DataFrame) -> None:
    """Validate labels and probabilities before converting them to risk."""
    prediction_columns = ["flood_prediction", "cyclone_prediction"]
    probability_columns = ["flood_probability", "cyclone_probability"]
    drought_available = bool(
        dataframe.get("drought_available", pd.Series(True, index=dataframe.index)).all()
    )
    if drought_available:
        prediction_columns.append("drought_prediction")
        probability_columns.append("drought_probability")
    for column in prediction_columns:
        invalid = ~dataframe[column].isin([0, 1])
        if invalid.any():
            raise ValueError(f"{column} must contain only 0 or 1.")
    for column in probability_columns:
        values = pd.to_numeric(dataframe[column], errors="coerce")
        if values.isna().any() or not values.between(0.0, 1.0).all():
            raise ValueError(f"{column} must contain probabilities from 0 to 1.")


# ==========================================================
# RISK LEVELS
# ==========================================================

NONE = 0

LOW = 1

MODERATE = 2

HIGH = 3

EXTREME = 4


RISK_LEVELS = {

    NONE: "NONE",

    LOW: "LOW",

    MODERATE: "MODERATE",

    HIGH: "HIGH",

    EXTREME: "EXTREME",

}


RISK_LABELS = {

    "NONE": NONE,

    "LOW": LOW,

    "MODERATE": MODERATE,

    "HIGH": HIGH,

    "EXTREME": EXTREME,

}


# ==========================================================
# PROBABILITY THRESHOLDS
# ==========================================================

#
# Probability
#
# 0.00 - 0.20  -> NONE
# 0.20 - 0.40  -> LOW
# 0.40 - 0.60  -> MODERATE
# 0.60 - 0.80  -> HIGH
# 0.80 - 1.00  -> EXTREME
#

NONE_THRESHOLD = 0.20

LOW_THRESHOLD = 0.40

MODERATE_THRESHOLD = 0.60

HIGH_THRESHOLD = 0.80

EXTREME_THRESHOLD = 1.00


# ==========================================================
# OUTPUT COLUMNS
# ==========================================================

RISK_SCORE_COLUMNS = [

    "flood_risk_score",

    "drought_risk_score",

    "cyclone_risk_score",

    "overall_risk_score",

]


RISK_LEVEL_COLUMNS = [

    "flood_risk_level",

    "drought_risk_level",

    "cyclone_risk_level",

    "overall_risk_level",

]


OUTPUT_COLUMNS = (

    METADATA_COLUMNS

    + RISK_SCORE_COLUMNS

    + RISK_LEVEL_COLUMNS

)


# ==========================================================
# DATACLASSES
# ==========================================================

@dataclass(slots=True, frozen=True)
class RiskScore:
    """
    Numerical risk scores.
    """

    flood: int

    drought: int

    cyclone: int

    overall: int


@dataclass(slots=True, frozen=True)
class RiskLevel:
    """
    Human-readable risk levels.
    """

    flood: str

    drought: str

    cyclone: str

    overall: str


# ==========================================================
# DEFAULTS
# ==========================================================

DEFAULT_SCORE = RiskScore(

    flood=NONE,

    drought=NONE,

    cyclone=NONE,

    overall=NONE,

)


DEFAULT_LEVEL = RiskLevel(

    flood="NONE",

    drought="NONE",

    cyclone="NONE",

    overall="NONE",

)


# ==========================================================
# HELPERS
# ==========================================================

def score_to_level(
    score: int,
) -> str:
    """
    Convert score to risk level.
    """

    return RISK_LEVELS.get(

        score,

        "UNKNOWN",

    )


def level_to_score(
    level: str,
) -> int:
    """
    Convert risk level to score.
    """

    return RISK_LABELS.get(

        level.upper(),

        NONE,

    )


# ==========================================================
# EXPORTS
# ==========================================================

__all__ = [

    "METADATA_COLUMNS",

    "PREDICTION_COLUMNS",

    "PROBABILITY_COLUMNS",

    "REQUIRED_COLUMNS",

    "NONE",

    "LOW",

    "MODERATE",

    "HIGH",

    "EXTREME",

    "NONE_THRESHOLD",

    "LOW_THRESHOLD",

    "MODERATE_THRESHOLD",

    "HIGH_THRESHOLD",

    "EXTREME_THRESHOLD",

    "RISK_LEVELS",

    "RISK_LABELS",

    "RISK_SCORE_COLUMNS",

    "RISK_LEVEL_COLUMNS",

    "OUTPUT_COLUMNS",

    "RiskScore",

    "RiskLevel",

    "DEFAULT_SCORE",

    "DEFAULT_LEVEL",

    "score_to_level",

    "level_to_score",

]
