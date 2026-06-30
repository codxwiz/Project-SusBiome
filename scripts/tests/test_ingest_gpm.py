"""
============================================================
Integration Test
NASA GPM Ingestion Pipeline
============================================================
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from scripts.sources.common.auth import AuthManager
from scripts.sources.common.storage import Storage
from scripts.sources.common.downloader import Downloader
from scripts.sources.common.manifest import ManifestCatalog

from scripts.sources.nasa.client import NASAClient
from scripts.sources.nasa.discovery import NASAEarthdataDiscovery
from scripts.sources.nasa.models import Product
from scripts.sources.nasa.gpm.ingest_gpm import GPMIngestor


# ==========================================================
# CONFIGURATION
# ==========================================================

ROOT = Path("data")

MANIFEST = ROOT / "manifest.csv"


# ==========================================================
# PRODUCT
# ==========================================================

product = Product(

    provider="NASA",

    product="GPM_3IMERGDF",

    version="07",

    description=(
        "IMERG Final Daily "
        "Precipitation"
    ),

    file_extension=".nc4",

)


# ==========================================================
# DEPENDENCIES
# ==========================================================

auth = AuthManager()

storage = Storage(

    root=ROOT,

)

manifest = ManifestCatalog(

    manifest_path=MANIFEST,

)

downloader = Downloader(

    auth=auth,

    storage=storage,

)

client = NASAClient(
    auth=auth,
)

discovery = NASAEarthdataDiscovery(
    client=client,
)

ingestor = GPMIngestor(

    discovery=discovery,

    downloader=downloader,

    storage=storage,

    manifest=manifest,

)


# ==========================================================
# RUN
# ==========================================================

print()

print("=" * 60)

print("STARTING GPM INGESTION TEST")

print("=" * 60)

print()

ingestor.run(

    product=product,

    start_date=datetime(

        2024,

        7,

        1,

    ),

    end_date=datetime(

        2024,

        7,

        1,

    ),

)

print()

print("=" * 60)

print("INGESTION FINISHED")

print("=" * 60)

print()

print("Manifest Summary")

print("----------------")

print(

    manifest.summary()

)

print()

print("Failed Datasets")

print("----------------")

print(

    manifest.failed()

)

print()

print("=" * 60)

print("TEST COMPLETE")

print("=" * 60)