import xarray as xr
import pandas as pd

print("Loading ERA5 datasets...")

# Instant variables
instant_ds = xr.open_dataset(
    "data/raw/era5/extracted/data_stream-oper_stepType-instant.nc",
    engine="netcdf4"
)

# Accumulated variables
accum_ds = xr.open_dataset(
    "data/raw/era5/extracted/data_stream-oper_stepType-accum.nc",
    engine="netcdf4"
)

# District coordinates
locations = pd.read_csv("data/raw/locations.csv")

results = []

print("Starting district extraction...")

# Loop through districts
for _, row in locations.iterrows():

    state = row["state"]
    district = row["district"]
    lat = row["latitude"]
    lon = row["longitude"]

    print(f"Processing {district}, {state}")

    # nearest point from instant dataset
    instant_point = instant_ds.sel(
        latitude=lat,
        longitude=lon,
        method="nearest"
    )

    # nearest point from rainfall dataset
    accum_point = accum_ds.sel(
        latitude=lat,
        longitude=lon,
        method="nearest"
    )

    # loop through dates
    for time in instant_point.valid_time.values:

        # temperature (Kelvin → Celsius)
        temp_k = instant_point["t2m"].sel(valid_time=time).values.item()
        temp_c = temp_k - 273.15

        # dewpoint
        dew_k = instant_point["d2m"].sel(valid_time=time).values.item()
        dew_c = dew_k - 273.15

        # pressure (Pa)
        pressure = instant_point["sp"].sel(valid_time=time).values.item()

        # wind components
        u10 = instant_point["u10"].sel(valid_time=time).values.item()
        v10 = instant_point["v10"].sel(valid_time=time).values.item()

        # rainfall (meters → mm)
        rain_m = accum_point["tp"].sel(valid_time=time).values.item()
        rain_mm = rain_m * 1000

        results.append({
            "date": str(time)[:10],
            "state": state,
            "district": district,
            "temperature": round(temp_c, 2),
            "rainfall": round(rain_mm, 2),
            "dewpoint": round(dew_c, 2),
            "u10": round(u10, 2),
            "v10": round(v10, 2),
            "pressure": round(pressure, 2)
        })

# dataframe
df = pd.DataFrame(results)

# save
df.to_csv(
    "data/processed/district_climate_raw.csv",
    index=False
)

print("District extraction completed successfully")