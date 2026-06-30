"""
==============================================================
Project SusBiome
Historical Ingestion Models
==============================================================

Shared models and constants for the historical data
ingestion pipeline.

Responsibilities
----------------
• Historical date ranges
• Dataset locations
• Provider configuration
• Common dataclasses
• Validation constants

This module contains NO download logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


# ==========================================================
# ROOT
# ==========================================================

DATA_DIRECTORY = Path("data")

BRONZE_DIRECTORY = DATA_DIRECTORY / "bronze"

SILVER_DIRECTORY = DATA_DIRECTORY / "silver"

FUSION_DIRECTORY = DATA_DIRECTORY / "fusion"


# ==========================================================
# PROVIDERS
# ==========================================================

ERA5_DIRECTORY = SILVER_DIRECTORY / "era5"

NASA_DIRECTORY = SILVER_DIRECTORY / "nasa"

GPM_DIRECTORY = SILVER_DIRECTORY / "gpm"


# ==========================================================
# OUTPUT
# ==========================================================

HISTORICAL_OUTPUT = (

    FUSION_DIRECTORY

    / "historical_unified.parquet"

)


# ==========================================================
# DEFAULT DATE RANGE
# ==========================================================

DEFAULT_START_DATE = date(

    2010,

    1,

    1,

)

DEFAULT_END_DATE = date.today()


# ==========================================================
# REQUIRED COLUMNS
# ==========================================================

REQUIRED_COLUMNS = [

    "latitude",

    "longitude",

    "valid_time",

]


# ==========================================================
# WEATHER VARIABLES
# ==========================================================

ERA5_VARIABLES = [

    "temperature",

    "precipitation",

    "pressure",

    "wind_speed",

]

NASA_VARIABLES = [

    "soil_moisture",

    "evapotranspiration",

    "vegetation_index",

]

GPM_VARIABLES = [

    "precipitation",

]


# ==========================================================
# PROVIDERS
# ==========================================================

PROVIDERS = [

    "ERA5",

    "NASA",

    "GPM",

]


# ==========================================================
# DATACLASSES
# ==========================================================

@dataclass(slots=True, frozen=True)
class DateRange:
    """
    Historical period.
    """

    start: date

    end: date


@dataclass(slots=True, frozen=True)
class DatasetPath:
    """
    Provider dataset.
    """

    provider: str

    directory: Path


@dataclass(slots=True, frozen=True)
class ProviderStatus:
    """
    Provider readiness.
    """

    provider: str

    available: bool

    files: int


# ==========================================================
# DEFAULT RANGE
# ==========================================================

DEFAULT_RANGE = DateRange(

    start=DEFAULT_START_DATE,

    end=DEFAULT_END_DATE,

)


# ==========================================================
# DATASET PATHS
# ==========================================================

DATASET_PATHS = {

    "ERA5": DatasetPath(

        "ERA5",

        ERA5_DIRECTORY,

    ),

    "NASA": DatasetPath(

        "NASA",

        NASA_DIRECTORY,

    ),

    "GPM": DatasetPath(

        "GPM",

        GPM_DIRECTORY,

    ),

}


# ==========================================================
# EXPORTS
# ==========================================================

__all__ = [

    "DATA_DIRECTORY",

    "BRONZE_DIRECTORY",

    "SILVER_DIRECTORY",

    "FUSION_DIRECTORY",

    "ERA5_DIRECTORY",

    "NASA_DIRECTORY",

    "GPM_DIRECTORY",

    "HISTORICAL_OUTPUT",

    "DEFAULT_START_DATE",

    "DEFAULT_END_DATE",

    "DEFAULT_RANGE",

    "REQUIRED_COLUMNS",

    "ERA5_VARIABLES",

    "NASA_VARIABLES",

    "GPM_VARIABLES",

    "PROVIDERS",

    "DateRange",

    "DatasetPath",

    "ProviderStatus",

    "DATASET_PATHS",

]