"""
============================================================
Test ERA5 Orchestrator
============================================================

Runs the complete ERA5 production pipeline.

ERA5 CDS
    ↓
Orchestrator
    ↓
Ingestor
    ↓
Parser
    ↓
Parquet
    ↓
Manifest

============================================================
"""

from pathlib import Path

from scripts.sources.common.manifest import ManifestCatalog
from scripts.sources.common.storage import Storage

from scripts.sources.era5.client import ERA5Client
from scripts.sources.era5.ingest_era5 import ERA5Ingestor
from scripts.sources.era5.models import Product
from scripts.sources.era5.orchestrator import ERA5Orchestrator


ROOT = Path("data")


storage = Storage(

    root=ROOT,

)

manifest = ManifestCatalog(

    manifest_path=ROOT / "manifest.csv",

)

client = ERA5Client()


ingestor = ERA5Ingestor(

    client=client,

    storage=storage,

    manifest=manifest,

)


orchestrator = ERA5Orchestrator(

    ingestor=ingestor,

)


product = Product(

    provider="ECMWF",

    dataset="reanalysis-era5-single-levels",

    description="ERA5 Single Levels",

    file_extension=".nc",

)


print()

print("=" * 60)

print("STARTING ERA5 ORCHESTRATOR TEST")

print("=" * 60)


output = orchestrator.run(

    product=product,

    variable="t2m",

    year=2024,

    month=7,

    day=1,

    hour="12:00",

)


print()

print("=" * 60)

print("ORCHESTRATION FINISHED")

print("=" * 60)

print()

print("Output")

print("------")

print(output)

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