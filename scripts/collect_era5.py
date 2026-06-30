import cdsapi

print("Connecting to ERA5...")

client = cdsapi.Client()

client.retrieve(
    "reanalysis-era5-single-levels",
    {
        "product_type": "reanalysis",
        "variable": [
            "2m_temperature",
            "2m_dewpoint_temperature",
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "surface_pressure",
            "total_precipitation",
        ],
        "year": "2023",
        "month": "01",
        "day": [
            "01",
            "02",
            "03",
            "04",
            "05",
        ],
        "time": "12:00",
        # Northeast India bounding box
        # North, West, South, East
        "area": [29.5, 88.0, 22.0, 97.5],
        "format": "netcdf",
    },
    "data/raw/era5/full_era5.zip",
)

print("ERA5 download complete")