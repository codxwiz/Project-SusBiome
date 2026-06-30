"""
============================================================
Test ERA5 Client
============================================================
"""

from pathlib import Path

from scripts.sources.era5.client import ERA5Client

client = ERA5Client()

destination = Path(
    "data/bronze/era5/test.nc"
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

print("STARTING ERA5 DOWNLOAD TEST")

print("=" * 60)

client.download(

    dataset="reanalysis-era5-single-levels",

    request=request,

    destination=destination,

)

print()

print("=" * 60)

print("DOWNLOAD COMPLETE")

print("=" * 60)

print(destination)