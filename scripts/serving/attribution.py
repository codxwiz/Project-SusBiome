"""Public source attribution for the operational weather outlook."""

from __future__ import annotations

SOURCES = [
    {
        "name": "India Meteorological Department RSMC New Delhi",
        "role": "Official cyclone bulletin confirmation",
        "url": "https://rsmcnewdelhi.imd.gov.in/",
        "license": "Government of India source; linked, not republished",
    },
    {
        "name": "Open-Meteo",
        "role": "3, 7, and 14-day weather forecast",
        "url": "https://open-meteo.com/",
        "license": "CC BY 4.0; production use subject to provider terms",
    },
    {
        "name": "Copernicus Climate Change Service ERA5",
        "role": "Historical weather, soil moisture, and runoff patterns",
        "url": "https://cds.climate.copernicus.eu/",
        "license": "Copernicus Products License",
    },
    {
        "name": "NASA Global Precipitation Measurement IMERG",
        "role": "Historical and near-real-time precipitation",
        "url": "https://gpm.nasa.gov/data/imerg",
        "license": "NASA Earth science data policy",
    },
    {
        "name": "NASA Shuttle Radar Topography Mission SRTMGL1",
        "role": "Approximately 30 m elevation and slope context",
        "url": "https://doi.org/10.5067/MEaSUREs/SRTM/SRTMGL1.003",
        "license": "NASA Earth science data policy",
    },
    {
        "name": "ESA WorldCover",
        "role": "10 m land-cover context",
        "url": "https://esa-worldcover.org/en/data-access",
        "license": "CC BY 4.0",
    },
    {
        "name": "UCSB Climate Hazards Center CHIRPS",
        "role": "Independent historical rainfall cross-check",
        "url": "https://www.chc.ucsb.edu/data/chirps",
        "license": "Public domain",
    },
    {
        "name": "OpenStreetMap contributors / Geofabrik",
        "role": "Current Northeast district boundary overrides",
        "url": "https://www.openstreetmap.org/copyright",
        "license": "Open Database License 1.0",
    },
    {
        "name": "geoBoundaries",
        "role": "Baseline India administrative boundaries",
        "url": "https://www.geoboundaries.org/",
        "license": "Open Database License 1.0",
    },
]

DISCLAIMER = (
    "Weather and physical land susceptibility index, not a disaster probability, "
    "population or asset vulnerability estimate, forecast guarantee, "
    "or official warning. Check IMD and local authorities before making safety decisions."
)

RISK_SCALE = [
    {"level": "LOW", "minimum": 0, "maximum": 24.9},
    {"level": "MODERATE", "minimum": 25, "maximum": 49.9},
    {"level": "HIGH", "minimum": 50, "maximum": 74.9},
    {"level": "VERY HIGH", "minimum": 75, "maximum": 100},
]
