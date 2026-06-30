import xarray as xr
import pandas as pd
import numpy as np

# Load ERA5 files
instant = xr.open_dataset(
    "data/raw/era5/extracted/data_stream-oper_stepType-instant.nc"
)

accum = xr.open_dataset(
    "data/raw/era5/extracted/data_stream-oper_stepType-accum.nc"
)

# District coordinates
locations = pd.read_csv("data/raw/locations.csv")

results = []

# Loop through districts
for _, row in locations.iterrows():

    state = row["state"]
    district = row["district"]
    lat = row["latitude"]
    lon = row["longitude"]

    print(f"Processing {district}, {state}")

    # nearest gridpoint
    inst_point = instant.sel(
        latitude=lat,
        longitude=lon,
        method="nearest"
    )

    rain_point = accum.sel(
        latitude=lat,
        longitude=lon,
        method="nearest"
    )

    # loop through dates
    for time in inst_point.valid_time.values:

        # temperature
        t2m = inst_point["t2m"].sel(valid_time=time).values.item()
        temp_c = t2m - 273.15

        # dewpoint
        d2m = inst_point["d2m"].sel(valid_time=time).values.item()
        dew_c = d2m - 273.15

        # humidity (approx RH formula)
        humidity = 100 * (
            np.exp((17.625 * dew_c)/(243.04 + dew_c)) /
            np.exp((17.625 * temp_c)/(243.04 + temp_c))
        )

        # wind speed
        u10 = inst_point["u10"].sel(valid_time=time).values.item()
        v10 = inst_point["v10"].sel(valid_time=time).values.item()

        wind_speed = np.sqrt((u10**2) + (v10**2))

        # pressure
        sp = inst_point["sp"].sel(valid_time=time).values.item()
        pressure = sp / 100

        # rainfall
        tp = rain_point["tp"].sel(valid_time=time).values.item()
        rainfall = tp * 1000

        results.append({
            "date": str(time)[:10],
            "state": state,
            "district": district,
            "temperature": round(temp_c, 2),
            "rainfall": round(rainfall, 2),
            "humidity": round(humidity, 2),
            "wind_speed": round(wind_speed, 2),
            "pressure": round(pressure, 2)
        })

# save
df = pd.DataFrame(results)

df.to_csv(
    "data/processed/district_climate_full.csv",
    index=False
)

print("District Pipeline V2 complete")