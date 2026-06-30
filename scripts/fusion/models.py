"""
============================================================
SusBiome Fusion Models
============================================================

Canonical data models used by the data fusion
pipeline.

Every provider (NASA, ERA5, IMD, etc.) is
converted into this common schema before
feature engineering and machine learning.

============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


NORTHEAST_INDIA_BOUNDS = {
    "min_latitude": 20.0,
    "max_latitude": 30.5,
    "min_longitude": 87.0,
    "max_longitude": 98.5,
}

NORTHEAST_INDIA_STATES = {
    "Arunachal Pradesh",
    "Assam",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Sikkim",
    "Tripura",
}


# ==========================================================
# LOCATION
# ==========================================================

@dataclass(frozen=True, slots=True)
class Location:
    """
    Geographic location.
    """

    latitude: float

    longitude: float


# ==========================================================
# OBSERVATION
# ==========================================================

@dataclass(slots=True)
class Observation:
    """
    One observation at one location and time.
    """

    location: Location

    valid_time: datetime

    values: dict[str, float]


# ==========================================================
# DATASET
# ==========================================================

@dataclass(frozen=True, slots=True)
class Dataset:
    """
    Unified fused dataset.
    """

    path: Path

    observations: int

    created_at: datetime
