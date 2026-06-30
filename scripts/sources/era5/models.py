"""
============================================================
ERA5 Data Models
============================================================

Purpose
-------
Shared ERA5 domain models.

These models are exchanged between the
ERA5 client, parser and ingestion pipeline.

============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# ==========================================================
# PRODUCT
# ==========================================================

@dataclass(frozen=True, slots=True)
class Product:
    """
    ERA5 dataset definition.
    """

    provider: str

    dataset: str

    description: str

    file_extension: str


# ==========================================================
# REQUEST
# ==========================================================

@dataclass(frozen=True, slots=True)
class Request:
    """
    One ERA5 download request.
    """

    product: Product

    start_time: datetime

    end_time: datetime

    variables: list[str]

    area: list[float]

    format: str = "netcdf"


# ==========================================================
# DOWNLOAD RECORD
# ==========================================================

@dataclass(slots=True)
class DownloadRecord:
    """
    Download result.
    """

    request: Request

    local_path: Path

    downloaded_at: datetime

    downloaded_bytes: int

    success: bool


# ==========================================================
# DATASET
# ==========================================================

@dataclass(frozen=True, slots=True)
class Dataset:
    """
    Parsed ERA5 dataset.
    """

    product: Product

    path: Path

    coverage_start: datetime

    coverage_end: datetime