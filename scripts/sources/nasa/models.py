"""
============================================================
NASA Data Models
============================================================

Purpose
-------
Shared NASA domain models.

Every NASA module exchanges these objects.

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

    provider: str

    product: str

    version: str

    description: str

    file_extension: str
    # ==========================================================
# GRANULE
# ==========================================================

@dataclass(slots=True)
class Granule:

    granule_id: str

    product: Product

    start_time: datetime

    end_time: datetime

    url: str

    size_bytes: int | None = None

    content_type: str | None = None

    checksum: str | None = None

    checksum_type: str | None = None
    # ==========================================================
# DOWNLOAD RECORD
# ==========================================================

@dataclass(slots=True)
class DownloadRecord:

    granule: Granule

    local_path: Path

    downloaded_at: datetime

    downloaded_bytes: int

    success: bool
    # ==========================================================
# COLLECTION
# ==========================================================

@dataclass(frozen=True, slots=True)
class Collection:

    name: str

    provider: str

    version: str