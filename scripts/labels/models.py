"""
============================================================
Label Engineering Models
============================================================

Shared configuration for the Label Engineering pipeline.

============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sources.common.config import PROJECT_ROOT

# ==========================================================
# INPUT / OUTPUT
# ==========================================================

DEFAULT_INPUT = PROJECT_ROOT / "data/gold/features.parquet"

DEFAULT_OUTPUT = PROJECT_ROOT / "data/gold/training.parquet"

# ==========================================================
# LABEL COLUMNS
# ==========================================================

FLOOD_LABEL = "flood_risk"

DROUGHT_LABEL = "drought_risk"

CYCLONE_LABEL = "cyclone_risk"

# ==========================================================
# LABEL MAPPING
# ==========================================================

LABELS = {

    "flood": FLOOD_LABEL,

    "drought": DROUGHT_LABEL,

    "cyclone": CYCLONE_LABEL,

}

# ==========================================================
# REQUIRED INPUT COLUMNS
# ==========================================================

REQUIRED_COLUMNS = [

    "longitude",

    "latitude",

    "valid_time",

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

]

# ==========================================================
# FLOOD LABEL THRESHOLDS
# ==========================================================

FLOOD_RAIN_1DAY = 100.0          # mm/day

FLOOD_RAIN_7DAY = 300.0          # mm/7 days

FLOOD_WET_DAYS = 5

# ==========================================================
# DROUGHT LABEL THRESHOLDS
# ==========================================================

DROUGHT_DRY_DAYS = 30

DROUGHT_RAIN_ANOMALY = -20.0

TEMPERATURE_ANOMALY = 2.0

# ==========================================================
# CYCLONE LABEL THRESHOLDS
# ==========================================================

CYCLONE_RAIN = 150.0

CYCLONE_TEMPERATURE = 300.0

# ==========================================================
# LABEL CONFIGURATION
# ==========================================================

@dataclass(slots=True, frozen=True)
class LabelConfig:

    input_path: Path = DEFAULT_INPUT

    output_path: Path = DEFAULT_OUTPUT

    flood_label: str = FLOOD_LABEL

    drought_label: str = DROUGHT_LABEL

    cyclone_label: str = CYCLONE_LABEL
