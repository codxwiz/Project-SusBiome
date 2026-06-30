"""
============================================================
Machine Learning Models
============================================================

Shared configuration for the Machine Learning pipeline.

============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sources.common.config import PROJECT_ROOT

# ==========================================================
# DATASET PATHS
# ==========================================================

TRAINING_DATASET = PROJECT_ROOT / "data/gold/features_historical"

MODEL_DIRECTORY = PROJECT_ROOT / "models"

# ==========================================================
# MODEL FILES
# ==========================================================

FLOOD_MODEL = MODEL_DIRECTORY / "flood_model.joblib"

DROUGHT_MODEL = MODEL_DIRECTORY / "drought_model.joblib"

CYCLONE_MODEL = MODEL_DIRECTORY / "cyclone_model.joblib"

# ==========================================================
# TARGET COLUMNS
# ==========================================================

TARGET_COLUMNS = [

    "flood_risk",

    "drought_risk",

    "cyclone_risk",

]

# Flood and cyclone determine production readiness. Drought remains available
# as an experimental target because Northeast India has few independent events.
PRODUCTION_TARGET_COLUMNS = ["flood_risk", "cyclone_risk"]
EXPERIMENTAL_TARGET_COLUMNS = ["drought_risk"]

# Canonical model input schema. Training and inference must import this
# single definition so saved estimators receive the same ordered features.
FEATURE_COLUMNS = [
    "precipitation",
    "value",
    "precipitation_7d_sum",
    "precipitation_30d_sum",
    "precipitation_90d_sum",
    "temperature_7d_mean",
    "temperature_30d_mean",
    "temperature_90d_mean",
    "temperature_anomaly",
    "precipitation_anomaly",
    "consecutive_dry_days",
    "consecutive_wet_days",
    "rainfall_intensity",
    "precipitation_3d_sum",
    "precipitation_14d_sum",
    "precipitation_180d_sum",
    "temperature_range",
    "relative_humidity_7d_mean",
    "surface_pressure_7d_mean",
    "pressure_anomaly",
    "wind_speed_3d_max",
    "wind_speed_7d_max",
    "antecedent_precipitation_index",
    "soil_moisture_30d_mean",
    "soil_moisture_anomaly",
    "runoff_7d_sum",
    "water_balance_30d",
    "year",
    "month",
    "day",
    "day_of_year",
    "week",
    "quarter",
    "season",
]

MIN_HISTORY_DAYS = 3650
MIN_POSITIVE_SAMPLES = 30
MAX_NEGATIVE_RATIO = 10
MIN_NEGATIVES_PER_PARTITION = 5_000

DROP_COLUMNS = [

    "longitude",

    "latitude",

    "valid_time",

]

# ==========================================================
# TARGET CONSTANTS
# ==========================================================

# Column names for each target
FLOOD_TARGET = "flood_risk"

DROUGHT_TARGET = "drought_risk"

CYCLONE_TARGET = "cyclone_risk"

# ==========================================================
# TARGET MAPPING
# ==========================================================

TARGETS = {

    "flood": FLOOD_TARGET,

    "drought": DROUGHT_TARGET,

    "cyclone": CYCLONE_TARGET,

}

# ==========================================================
# DATASET SPLITS
# ==========================================================

TRAIN_SIZE = 0.70

VALIDATION_SIZE = 0.15

TEST_SIZE = 0.15

RANDOM_STATE = 42

# ==========================================================
# DEFAULT ALGORITHM
# ==========================================================

DEFAULT_MODEL = "RandomForest"

# ==========================================================
# RANDOM FOREST PARAMETERS
# ==========================================================

RF_N_ESTIMATORS = 300

RF_MAX_DEPTH = 20

RF_MIN_SAMPLES_SPLIT = 5

RF_MIN_SAMPLES_LEAF = 2

RF_N_JOBS = -1

# ==========================================================
# EVALUATION METRICS
# ==========================================================

METRICS = [

    "accuracy",

    "precision",

    "recall",

    "f1",

    "roc_auc",

]

# ==========================================================
# FEATURES TO EXCLUDE
# ==========================================================

EXCLUDED_COLUMNS = [

    "longitude",

    "latitude",

    "valid_time",

]

# ==========================================================
# MODEL CONFIGURATION
# ==========================================================

@dataclass(slots=True, frozen=True)
class MLConfig:

    training_dataset: Path = TRAINING_DATASET

    model_directory: Path = MODEL_DIRECTORY

    flood_model: Path = FLOOD_MODEL

    drought_model: Path = DROUGHT_MODEL

    cyclone_model: Path = CYCLONE_MODEL

    train_size: float = TRAIN_SIZE

    validation_size: float = VALIDATION_SIZE

    test_size: float = TEST_SIZE

    random_state: int = RANDOM_STATE

    algorithm: str = DEFAULT_MODEL
