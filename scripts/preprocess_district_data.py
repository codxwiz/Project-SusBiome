import pandas as pd


# ==========================================
# LOAD DATASET
# ==========================================

df = pd.read_csv(
    "data/processed/district_climate_full.csv"
)


# ==========================================
# DATE FORMATTING
# ==========================================

df["date"] = pd.to_datetime(df["date"])
df["month"] = df["date"].dt.month

# IMPORTANT: sort before rolling calculations
df = df.sort_values(
    ["state", "district", "date"]
).reset_index(drop=True)


# ==========================================
# ROLLING FEATURES (FIXED VERSION)
# ==========================================

# 7 day rainfall average
df["rainfall_7day_avg"] = (
    df.groupby(["state", "district"])["rainfall"]
    .transform(
        lambda x: x.rolling(
            7,
            min_periods=1
        ).mean()
    )
)

# 30 day rainfall average
df["rainfall_30day_avg"] = (
    df.groupby(["state", "district"])["rainfall"]
    .transform(
        lambda x: x.rolling(
            30,
            min_periods=1
        ).mean()
    )
)

# 30 day temperature average
df["temp_30day_avg"] = (
    df.groupby(["state", "district"])["temperature"]
    .transform(
        lambda x: x.rolling(
            30,
            min_periods=1
        ).mean()
    )
)

# 30 day humidity average
df["humidity_30day_avg"] = (
    df.groupby(["state", "district"])["humidity"]
    .transform(
        lambda x: x.rolling(
            30,
            min_periods=1
        ).mean()
    )
)


# ==========================================
# PRESSURE ANOMALY
# ==========================================

pressure_avg = (
    df.groupby(["state", "district"])["pressure"]
    .transform(
        lambda x: x.rolling(
            30,
            min_periods=1
        ).mean()
    )
)

df["pressure_anomaly"] = (
    df["pressure"] - pressure_avg
)


# ==========================================
# RAINFALL ACCELERATION
# ==========================================

df["rainfall_acceleration"] = (
    df.groupby(["state", "district"])["rainfall"]
    .diff()
    .fillna(0)
)


# ==========================================
# CONSECUTIVE DRY DAYS
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


df["consecutive_dry_days"] = (
    df.groupby(["state", "district"])["rainfall"]
    .transform(count_dry_days)
)


# ==========================================
# SYNTHETIC TARGETS
# ==========================================

# Flood risk score
df["flood_risk_score"] = (
    (df["rainfall_30day_avg"] * 0.5)
    + (df["humidity"] * 0.3)
    + (df["rainfall_acceleration"] * 0.2)
)

# Drought risk score
df["drought_risk_score"] = (
    (df["temperature"] * 0.4)
    + (df["consecutive_dry_days"] * 0.4)
    - (df["rainfall_30day_avg"] * 0.2)
)

# Cyclone risk score
df["cyclone_risk_score"] = (
    (abs(df["pressure_anomaly"]) * 0.5)
    + (df["wind_speed"] * 0.3)
    + (df["humidity"] * 0.2)
)


# ==========================================
# SAVE DATASET
# ==========================================

df.to_csv(
    "data/training/model_dataset_v2.csv",
    index=False
)

print("Feature Engineering V2 complete")