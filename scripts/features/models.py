"""
============================================================
Feature Engineering Models
============================================================

Shared configuration for the Feature Engineering pipeline.

============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sources.common.config import PROJECT_ROOT

# ==========================================================
# INPUT / OUTPUT
# ==========================================================

DEFAULT_INPUT = PROJECT_ROOT / "data/fusion/unified.parquet"

DEFAULT_OUTPUT = PROJECT_ROOT / "data/gold/features.parquet"

# ==========================================================
# REQUIRED INPUT COLUMNS
# ==========================================================

REQUIRED_COLUMNS = [

    "longitude",

    "latitude",

    "valid_time",

    "precipitation",

    "value",

]

# ==========================================================
# ROLLING WINDOWS
# ==========================================================

ROLLING_WINDOWS = [

    7,

    30,

    90,

]

# ==========================================================
# DRY / WET THRESHOLDS
# ==========================================================

DRY_DAY_THRESHOLD = 1.0          # mm/day

HEAVY_RAIN_THRESHOLD = 50.0      # mm/day

HOT_DAY_THRESHOLD = 308.15       # Kelvin (35°C)

COLD_DAY_THRESHOLD = 273.15      # Kelvin (0°C)

# ==========================================================
# CALENDAR FEATURES
# ==========================================================

CALENDAR_COLUMNS = [

    "month",

    "day_of_year",

    "week",

    "season",

]

# ==========================================================
# FEATURE CONFIGURATION
# ==========================================================

@dataclass(slots=True, frozen=True)
class FeatureConfig:

    input_path: Path = DEFAULT_INPUT

    output_path: Path = DEFAULT_OUTPUT

    rolling_windows: tuple[int, ...] = (7, 30, 90)

    dry_threshold: float = DRY_DAY_THRESHOLD

    heavy_rain_threshold: float = HEAVY_RAIN_THRESHOLD

    hot_day_threshold: float = HOT_DAY_THRESHOLD

    cold_day_threshold: float = COLD_DAY_THRESHOLD
