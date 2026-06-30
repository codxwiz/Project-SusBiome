import cdsapi

print("Downloading wind test...")

client = cdsapi.Client()

client.retrieve(
    "reanalysis-era5-single-levels",
    {
        "product_type": "reanalysis",
        "variable": [
            "10m_u_component_of_wind",
            "10m_v_component_of_wind"
        ],
        "year": "2023",
        "month": "01",
        "day": ["01"],
        "time": "12:00",
        "area": [29.5, 88.0, 22.0, 97.5],
        "format": "netcdf"
    },
    "data/raw/era5/test_wind.nc"
)

print("Wind download complete")