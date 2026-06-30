"""Hazard-specific feature engineering over partitioned daily weather data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from scripts.ml.models import FEATURE_COLUMNS
from scripts.sources.common.config import PROJECT_ROOT

INPUT_ROOT = PROJECT_ROOT / "data/gold/training"
OUTPUT_ROOT = PROJECT_ROOT / "data/gold/features_historical"
GRID = ["latitude", "longitude"]


def _rolling(dataframe: pd.DataFrame, column: str, window: int, operation: str) -> pd.Series:
    grouped = dataframe.groupby(GRID, sort=False)[column]
    if operation == "sum":
        return grouped.transform(lambda values: values.rolling(window, min_periods=1).sum())
    if operation == "mean":
        return grouped.transform(lambda values: values.rolling(window, min_periods=1).mean())
    if operation == "max":
        return grouped.transform(lambda values: values.rolling(window, min_periods=1).max())
    raise ValueError(f"Unsupported rolling operation: {operation}")


def _streak(dataframe: pd.DataFrame, condition: pd.Series) -> pd.Series:
    output = pd.Series(0, index=dataframe.index, dtype="int32")
    for _, indexes in dataframe.groupby(GRID, sort=False).groups.items():
        values = condition.loc[indexes]
        blocks = (~values).cumsum()
        output.loc[indexes] = values.astype("int8").groupby(blocks).cumsum().astype("int32")
    return output


def build_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    required = {
        "valid_time", "latitude", "longitude", "precipitation", "temperature",
        "temperature_min", "temperature_max", "relative_humidity",
        "surface_pressure_hpa", "wind_speed", "wind_speed_max",
        "soil_moisture_surface", "runoff", "potential_evaporation",
    }
    missing = required - set(dataframe.columns)
    if missing:
        raise ValueError("Historical weather is missing: " + ", ".join(sorted(missing)))
    result = dataframe.copy()
    result["valid_time"] = pd.to_datetime(result["valid_time"], utc=True)
    result = result.sort_values([*GRID, "valid_time"]).reset_index(drop=True)

    for window in (3, 7, 14, 30, 90, 180):
        result[f"precipitation_{window}d_sum"] = _rolling(result, "precipitation", window, "sum")
    for window in (7, 30, 90):
        result[f"temperature_{window}d_mean"] = _rolling(result, "temperature", window, "mean")

    result["temperature_range"] = result["temperature_max"] - result["temperature_min"]
    result["relative_humidity_7d_mean"] = _rolling(result, "relative_humidity", 7, "mean")
    result["surface_pressure_7d_mean"] = _rolling(result, "surface_pressure_hpa", 7, "mean")
    pressure_baseline = _rolling(result, "surface_pressure_hpa", 30, "mean")
    result["pressure_anomaly"] = result["surface_pressure_hpa"] - pressure_baseline
    result["wind_speed_3d_max"] = _rolling(result, "wind_speed_max", 3, "max")
    result["wind_speed_7d_max"] = _rolling(result, "wind_speed_max", 7, "max")
    result["temperature_anomaly"] = result["temperature"] - _rolling(result, "temperature", 365, "mean")
    result["precipitation_anomaly"] = result["precipitation"] - _rolling(result, "precipitation", 365, "mean")
    result["antecedent_precipitation_index"] = result.groupby(GRID, sort=False)["precipitation"].transform(
        lambda values: values.ewm(alpha=0.15, adjust=False).mean()
    )
    result["soil_moisture_30d_mean"] = _rolling(result, "soil_moisture_surface", 30, "mean")
    result["soil_moisture_anomaly"] = (
        result["soil_moisture_surface"]
        - _rolling(result, "soil_moisture_surface", 365, "mean")
    )
    result["runoff_7d_sum"] = _rolling(result, "runoff", 7, "sum")
    result["water_balance_30d"] = (
        _rolling(result, "precipitation", 30, "sum")
        - _rolling(result, "potential_evaporation", 30, "sum")
    )
    result["consecutive_dry_days"] = _streak(result, result["precipitation"] < 1.0)
    result["consecutive_wet_days"] = _streak(result, result["precipitation"] >= 1.0)
    result["rainfall_intensity"] = (result["precipitation"] >= 50.0).astype("int8")

    time = result["valid_time"]
    result["year"] = time.dt.year
    result["month"] = time.dt.month
    result["day"] = time.dt.day
    result["day_of_year"] = time.dt.dayofyear
    result["week"] = time.dt.isocalendar().week.astype("int16")
    result["quarter"] = time.dt.quarter
    result["season"] = ((time.dt.month % 12) // 3) + 1
    result["value"] = result["temperature"]

    missing_features = [column for column in FEATURE_COLUMNS if column not in result]
    if missing_features:
        raise ValueError("Feature generation missed: " + ", ".join(missing_features))
    if result[FEATURE_COLUMNS].isna().any().any():
        raise ValueError("Hazard features contain missing values.")
    return result


def build_year(year: int, *, input_root: Path = INPUT_ROOT, output_root: Path = OUTPUT_ROOT) -> Path:
    current_path = input_root / f"year={year:04d}" / "training.parquet"
    if not current_path.exists():
        raise FileNotFoundError(current_path)
    current = pd.read_parquet(current_path)
    frames = [current]
    previous_path = input_root / f"year={year - 1:04d}" / "training.parquet"
    if previous_path.exists():
        previous = pd.read_parquet(previous_path)
        cutoff = pd.to_datetime(previous["valid_time"], utc=True).max() - pd.Timedelta(days=365)
        frames.insert(0, previous[pd.to_datetime(previous["valid_time"], utc=True) >= cutoff])
    features = build_features(pd.concat(frames, ignore_index=True))
    features = features[features["valid_time"].dt.year == year].reset_index(drop=True)
    destination = output_root / f"year={year:04d}" / "features.parquet"
    destination.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(destination, index=False, compression="snappy")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2006)
    parser.add_argument("--end-year", type=int, default=2025)
    arguments = parser.parse_args()
    result = {"completed": [], "failed": {}}
    for year in range(arguments.start_year, arguments.end_year + 1):
        try:
            result["completed"].append(str(build_year(year)))
        except Exception as error:
            result["failed"][str(year)] = str(error)
    print(json.dumps(result, indent=2))
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
