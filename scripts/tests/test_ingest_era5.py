"""
============================================================
Test ERA5 Ingestion
============================================================

Runs the complete ERA5 ingestion pipeline.

CDS
    ↓
Download
    ↓
Parser
    ↓
Parquet
    ↓
Manifest

============================================================
"""

from datetime import datetime
from pathlib import Path

from scripts.sources.common.manifest import ManifestCatalog
from scripts.sources.common.storage import Storage

from scripts.sources.era5.client import ERA5Client
from scripts.sources.era5.ingest_era5 import ERA5Ingestor
from scripts.sources.era5.models import Product


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


product = Product(

    provider="ECMWF",

    dataset="reanalysis-era5-single-levels",

    description="ERA5 Single Levels",

    file_extension=".nc",

)


request = {

    "product_type": "reanalysis",

    "variable": [

        "2m_temperature",

    ],

    "year": "2024",

    "month": "07",

    "day": "01",

    "time": [

        "12:00",

    ],

    "format": "netcdf",

}


print()

print("=" * 60)

print("STARTING ERA5 INGESTION TEST")

print("=" * 60)


output = ingestor.run(

    product=product,

    request=request,

    variable="t2m",

    year=2024,

    month=7,

)


print()

print("=" * 60)

print("INGESTION FINISHED")

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