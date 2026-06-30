"""
==============================================================
Project SusBiome
Prediction Models
==============================================================

Shared constants, configuration and data models used by the
Prediction package.

This module intentionally contains NO prediction logic.

Responsibilities
----------------
• Model file locations
• Required feature schema
• Prediction output schema
• Dataclasses
• Validation constants

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from scripts.ml.models import FEATURE_COLUMNS, MODEL_DIRECTORY


# ==========================================================
# MODEL STORAGE
# ==========================================================

FLOOD_MODEL = MODEL_DIRECTORY / "flood_model.joblib"

DROUGHT_MODEL = MODEL_DIRECTORY / "drought_model.joblib"

CYCLONE_MODEL = MODEL_DIRECTORY / "cyclone_model.joblib"


# ==========================================================
# INPUT FEATURE COLUMNS
# ==========================================================

# ==========================================================
# METADATA COLUMNS
# ==========================================================

METADATA_COLUMNS = [

    "longitude",

    "latitude",

    "valid_time",

]


# ==========================================================
# REQUIRED INPUT
# ==========================================================

REQUIRED_COLUMNS = (

    METADATA_COLUMNS

    + FEATURE_COLUMNS

)


# ==========================================================
# PREDICTION OUTPUT
# ==========================================================

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


OUTPUT_COLUMNS = (

    METADATA_COLUMNS

    + PREDICTION_COLUMNS

)


# ==========================================================
# MODEL NAMES
# ==========================================================

MODEL_NAMES = [

    "flood",

    "drought",

    "cyclone",

]


# ==========================================================
# PREDICTION LABELS
# ==========================================================

NEGATIVE_LABEL = 0

POSITIVE_LABEL = 1


# ==========================================================
# DATACLASSES
# ==========================================================

@dataclass(slots=True, frozen=True)
class PredictionInput:
    """
    Single prediction request.
    """

    longitude: float

    latitude: float

    valid_time: object


@dataclass(slots=True, frozen=True)
class PredictionOutput:
    """
    Prediction result.
    """

    flood_prediction: int

    drought_prediction: int

    cyclone_prediction: int


@dataclass(slots=True, frozen=True)
class PredictionProbability:
    """
    Prediction probabilities.

    Values should range from 0.0 to 1.0.
    """

    flood_probability: float

    drought_probability: float

    cyclone_probability: float


# ==========================================================
# DEFAULTS
# ==========================================================

DEFAULT_OUTPUT = PredictionOutput(

    flood_prediction=NEGATIVE_LABEL,

    drought_prediction=NEGATIVE_LABEL,

    cyclone_prediction=NEGATIVE_LABEL,

)


DEFAULT_PROBABILITY = PredictionProbability(

    flood_probability=0.0,

    drought_probability=0.0,

    cyclone_probability=0.0,

)


# ==========================================================
# VALIDATION
# ==========================================================

SUPPORTED_EXTENSIONS = [

    ".joblib",

]

SUPPORTED_MODELS = [

    FLOOD_MODEL,

    DROUGHT_MODEL,

    CYCLONE_MODEL,

]


# ==========================================================
# EXPORTS
# ==========================================================

__all__ = [

    "MODEL_DIRECTORY",

    "FLOOD_MODEL",

    "DROUGHT_MODEL",

    "CYCLONE_MODEL",

    "FEATURE_COLUMNS",

    "METADATA_COLUMNS",

    "REQUIRED_COLUMNS",

    "PREDICTION_COLUMNS",

    "PROBABILITY_COLUMNS",

    "OUTPUT_COLUMNS",

    "MODEL_NAMES",

    "NEGATIVE_LABEL",

    "POSITIVE_LABEL",

    "PredictionInput",

    "PredictionOutput",

    "PredictionProbability",

    "DEFAULT_OUTPUT",

    "DEFAULT_PROBABILITY",

    "SUPPORTED_EXTENSIONS",

    "SUPPORTED_MODELS",

]
