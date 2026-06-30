import pandas as pd
import os
import glob


# ==========================================
# LOAD ALL WEATHER FILES
# ==========================================

file_paths = glob.glob("data/raw/*_weather.csv")
all_data = []


# ==========================================
# READ FILES
# ==========================================

for file in file_paths:

    filename = os.path.basename(file)
    state = filename.replace("_weather.csv", "").replace("_", " ").title()

    print(f"Processing {state}...")

    df = pd.read_csv(file)
    df["state"] = state

    all_data.append(df)


# ==========================================
# COMBINE DATA
# ==========================================

master_df = pd.concat(all_data, ignore_index=True)

master_df["date"] = pd.to_datetime(master_df["date"])
master_df["month"] = master_df["date"].dt.month


# ==========================================
# ROLLING FEATURES
# ==========================================

master_df["rainfall_7day_avg"] = (
    master_df.groupby("state")["rainfall"]
    .rolling(7, min_periods=1)
    .mean()
    .reset_index(0, drop=True)
)

master_df["rainfall_30day_avg"] = (
    master_df.groupby("state")["rainfall"]
    .rolling(30, min_periods=1)
    .mean()
    .reset_index(0, drop=True)
)

master_df["rainfall_90day_avg"] = (
    master_df.groupby("state")["rainfall"]
    .rolling(90, min_periods=1)
    .mean()
    .reset_index(0, drop=True)
)

master_df["temp_90day_avg"] = (
    master_df.groupby("state")["temperature"]
    .rolling(90, min_periods=1)
    .mean()
    .reset_index(0, drop=True)
)

master_df["humidity_90day_avg"] = (
    master_df.groupby("state")["humidity"]
    .rolling(90, min_periods=1)
    .mean()
    .reset_index(0, drop=True)
)


# ==========================================
# PRESSURE ANOMALY
# ==========================================

pressure_avg = (
    master_df.groupby("state")["pressure"]
    .rolling(30, min_periods=1)
    .mean()
    .reset_index(0, drop=True)
)

master_df["pressure_anomaly"] = master_df["pressure"] - pressure_avg


# ==========================================
# RAINFALL ACCELERATION
# ==========================================

master_df["rainfall_acceleration"] = (
    master_df.groupby("state")["rainfall"]
    .diff()
)

master_df["rainfall_acceleration"] = (
    master_df["rainfall_acceleration"].fillna(0)
)


# ==========================================
# FIXED CONSECUTIVE DRY DAYS
# ==========================================

def count_dry_days(series):

    counter = 0
    result = []

    for rain in series:

        if rain == 0:
            counter += 1
        else:
            counter = 0

        result.append(counter)

    return result


master_df["consecutive_dry_days"] = (
    master_df.groupby("state")["rainfall"]
    .transform(count_dry_days)
)


# ==========================================
# SYNTHETIC TARGETS
# ==========================================

# Flood risk score
master_df["flood_risk_score"] = (
    (master_df["rainfall_90day_avg"] * 0.5)
    + (master_df["humidity"] * 0.3)
    + (master_df["rainfall_acceleration"] * 0.2)
)


# Drought risk score
master_df["drought_risk_score"] = (
    (master_df["temperature"] * 0.4)
    + (master_df["consecutive_dry_days"] * 0.4)
    - (master_df["rainfall_90day_avg"] * 0.2)
)


# Cyclone risk score
master_df["cyclone_risk_score"] = (
    (abs(master_df["pressure_anomaly"]) * 0.5)
    + (master_df["wind_speed"] * 0.3)
    + (master_df["humidity"] * 0.2)
)


# ==========================================
# SAVE FILES
# ==========================================

master_df.to_csv(
    "data/processed/combined_weather_data.csv",
    index=False
)

master_df.to_csv(
    "data/training/model_dataset.csv",
    index=False
)

print("Feature Engineering V3 completed successfully")