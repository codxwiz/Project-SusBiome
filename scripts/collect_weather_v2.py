import requests
import pandas as pd
from datetime import date
import time

# Load district locations
locations = pd.read_csv("data/raw/locations.csv")

# Time chunks
DATE_RANGES = [
    ("2010-01-01", "2012-12-31"),
    ("2013-01-01", "2015-12-31"),
    ("2016-01-01", "2018-12-31"),
    ("2019-01-01", "2021-12-31"),
    ("2022-01-01", date.today().strftime("%Y-%m-%d"))
]

all_data = []

for _, row in locations.iterrows():

    state = row["state"]
    district = row["district"]
    lat = row["latitude"]
    lon = row["longitude"]

    print(f"\nCollecting {district}, {state}")

    for start_date, end_date in DATE_RANGES:

        print(f"  {start_date} → {end_date}")

        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={lat}"
            f"&longitude={lon}"
            f"&start_date={start_date}"
            f"&end_date={end_date}"
            f"&daily=temperature_2m_mean,"
            f"precipitation_sum,"
            f"relative_humidity_2m_mean,"
            f"wind_speed_10m_max,"
            f"surface_pressure_mean"
            f"&timezone=auto"
        )

        try:
            response = requests.get(url, timeout=60)
            data = response.json()

            # detect API error
            if "daily" not in data:
                print("  API failed:", data)
                continue

            daily = data["daily"]

            for i in range(len(daily["time"])):

                all_data.append({
                    "date": daily["time"][i],
                    "state": state,
                    "district": district,
                    "latitude": lat,
                    "longitude": lon,
                    "temperature": daily["temperature_2m_mean"][i],
                    "rainfall": daily["precipitation_sum"][i],
                    "humidity": daily["relative_humidity_2m_mean"][i],
                    "wind_speed": daily["wind_speed_10m_max"][i],
                    "pressure": daily["surface_pressure_mean"][i]
                })

            time.sleep(2)

        except Exception as e:
            print("FAILED:", district, start_date, e)

# Save master file
df = pd.DataFrame(all_data)

df.to_csv(
    "data/raw/district_weather_master.csv",
    index=False
)

print("\nCollection complete")