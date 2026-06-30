import xarray as xr
import pandas as pd

# Load rainfall dataset
ds = xr.open_dataset(
    "data/raw/era5/extracted/data_stream-oper_stepType-accum.nc",
    engine="netcdf4"
)

locations = pd.read_csv("data/raw/locations.csv")

results = []

for _, row in locations.iterrows():

    state = row["state"]
    district = row["district"]
    lat = row["latitude"]
    lon = row["longitude"]

    print(f"Processing {district}, {state}")

    point = ds.sel(
        latitude=lat,
        longitude=lon,
        method="nearest"
    )

    for time in point.valid_time.values:

        # precipitation in meters → convert to mm
        rainfall_m = point["tp"].sel(valid_time=time).values.item()
        rainfall_mm = rainfall_m * 1000

        results.append({
            "date": str(time)[:10],
            "state": state,
            "district": district,
            "rainfall": round(rainfall_mm, 2)
        })

df = pd.DataFrame(results)

df.to_csv("data/processed/district_rainfall.csv", index=False)

print("Rainfall extraction completed")