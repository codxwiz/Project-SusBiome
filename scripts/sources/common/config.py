"""
============================================================
SusBiome Configuration
============================================================

Purpose
-------
Central configuration for the SusBiome platform.

This module contains ONLY configuration.

No filesystem logic.
No networking.
No business logic.

============================================================
"""
from __future__ import annotations

import os

from pathlib import Path
# ==========================================================
# PROJECT ROOT
# ==========================================================

PROJECT_ROOT = Path(

    __file__

).resolve().parents[3]
# ==========================================================
# DATA DIRECTORIES
# ==========================================================

DATA_DIR = PROJECT_ROOT / "data"

BRONZE_DIR = DATA_DIR / "bronze"

SILVER_DIR = DATA_DIR / "silver"

GOLD_DIR = DATA_DIR / "gold"

LOG_DIR = DATA_DIR / "logs"

METADATA_DIR = DATA_DIR / "metadata"

TEMP_DIR = DATA_DIR / "temp"
# ==========================================================
# ENVIRONMENT VARIABLES
# ==========================================================

EARTHDATA_TOKEN = os.getenv(

    "EARTHDATA_TOKEN"

)

IMD_API_KEY = os.getenv(

    "IMD_API_KEY"

)
# ==========================================================
# USER AGENT
# ==========================================================

USER_AGENT = (

    "SusBiome/1.0"

)
# ==========================================================
# HTTP CONFIGURATION
# ==========================================================

HTTP_TIMEOUT = 60

CONNECT_TIMEOUT = 15

READ_TIMEOUT = 60

VERIFY_SSL = True
# ==========================================================
# DOWNLOAD CONFIGURATION
# ==========================================================

DOWNLOAD_CHUNK_SIZE = 1024 * 1024

MAX_DOWNLOAD_WORKERS = 4

OVERWRITE_EXISTING = False

RESUME_DOWNLOADS = True
# ==========================================================
# RETRY CONFIGURATION
# ==========================================================

MAX_RETRIES = 5

INITIAL_RETRY_DELAY = 2

BACKOFF_MULTIPLIER = 2

MAX_RETRY_DELAY = 60
# ==========================================================
# LOGGING
# ==========================================================

LOG_LEVEL = "INFO"

LOG_FORMAT = (

    "%(asctime)s | %(levelname)s | %(message)s"

)
# ==========================================================
# STORAGE
# ==========================================================

PARQUET_COMPRESSION = "snappy"
# ==========================================================
# PROVIDERS
# ==========================================================

PROVIDER_NASA = "NASA"

PROVIDER_IMD = "IMD"

PROVIDER_GDELT = "GDELT"

PROVIDER_CWC = "CWC"

PROVIDER_NDMA = "NDMA"

SUPPORTED_PROVIDERS = (

    PROVIDER_NASA,

    PROVIDER_IMD,

    PROVIDER_GDELT,

    PROVIDER_CWC,

    PROVIDER_NDMA,

)
# ==========================================================
# NASA PRODUCTS
# ==========================================================

NASA_PRODUCT_GPM = "GPM"

NASA_PRODUCT_SMAP = "SMAP"

NASA_PRODUCT_MODIS = "MODIS"

SUPPORTED_NASA_PRODUCTS = (

    NASA_PRODUCT_GPM,

    NASA_PRODUCT_SMAP,

    NASA_PRODUCT_MODIS,

)
# ==========================================================
# STORAGE LAYERS
# ==========================================================

LAYER_BRONZE = "bronze"

LAYER_SILVER = "silver"

LAYER_GOLD = "gold"

LAYER_LOGS = "logs"

LAYER_METADATA = "metadata"

LAYER_TEMP = "temp"

SUPPORTED_LAYERS = (

    LAYER_BRONZE,

    LAYER_SILVER,

    LAYER_GOLD,

    LAYER_LOGS,

    LAYER_METADATA,

    LAYER_TEMP,

)
# ==========================================================
# DATASET STATUS
# ==========================================================

STATUS_PENDING = "PENDING"

STATUS_DOWNLOADING = "DOWNLOADING"

STATUS_DOWNLOADED = "DOWNLOADED"

STATUS_VALIDATED = "VALIDATED"

STATUS_PARSED = "PARSED"

STATUS_FAILED = "FAILED"

DATASET_STATUS = (

    STATUS_PENDING,

    STATUS_DOWNLOADING,

    STATUS_DOWNLOADED,

    STATUS_VALIDATED,

    STATUS_PARSED,

    STATUS_FAILED,

)
# ==========================================================
# FILE FORMATS
# ==========================================================

FORMAT_PARQUET = "parquet"

FORMAT_CSV = "csv"

FORMAT_JSON = "json"

FORMAT_NETCDF = "netcdf"

FORMAT_HDF5 = "hdf5"

SUPPORTED_FORMATS = (

    FORMAT_PARQUET,

    FORMAT_CSV,

    FORMAT_JSON,

    FORMAT_NETCDF,

    FORMAT_HDF5,

)
# ==========================================================
# PLATFORM
# ==========================================================

PLATFORM_NAME = "SusBiome"

PLATFORM_VERSION = "1.0.0"

DEFAULT_TIMEZONE = "UTC"
# ==========================================================
# NASA
# ==========================================================

NASA_IMERG_VERSION = "V07"

NASA_GPM_DATASET = "IMERG Final Run"

NASA_DEFAULT_PROVIDER = PROVIDER_NASA
# ==========================================================
# CONFIG VALIDATION
# ==========================================================

def validate_config() -> None:
    """
    Validate the platform configuration.
    """

    if not PROJECT_ROOT.exists():

        raise RuntimeError(

            f"Project root not found: {PROJECT_ROOT}"

        )

    if HTTP_TIMEOUT <= 0:

        raise ValueError(

            "HTTP_TIMEOUT must be greater than zero."

        )

    if MAX_RETRIES < 0:

        raise ValueError(

            "MAX_RETRIES cannot be negative."

        )
    # ==========================================================
# CONFIG
# ==========================================================

class Config:
    """
    Read-only platform configuration.
    """

    PROJECT_ROOT = PROJECT_ROOT

    DATA_DIR = DATA_DIR

    BRONZE_DIR = BRONZE_DIR

    SILVER_DIR = SILVER_DIR

    GOLD_DIR = GOLD_DIR

    LOG_DIR = LOG_DIR

    METADATA_DIR = METADATA_DIR

    TEMP_DIR = TEMP_DIR

    USER_AGENT = USER_AGENT

    HTTP_TIMEOUT = HTTP_TIMEOUT

    CONNECT_TIMEOUT = CONNECT_TIMEOUT

    READ_TIMEOUT = READ_TIMEOUT

    MAX_RETRIES = MAX_RETRIES

    DOWNLOAD_CHUNK_SIZE = DOWNLOAD_CHUNK_SIZE

    MAX_DOWNLOAD_WORKERS = MAX_DOWNLOAD_WORKERS

    PARQUET_COMPRESSION = PARQUET_COMPRESSION
    validate_config()