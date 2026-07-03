"""Build district drought episodes from long-term weather patterns, not disaster labels."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from scripts.sources.common.config import PROJECT_ROOT

FEATURE_ROOT = PROJECT_ROOT / "data/gold/features_historical"
LOCATIONS = PROJECT_ROOT / "data/raw/locations.csv"
OUTPUT = PROJECT_ROOT / "data/silver/events/weather_drought_episodes.parquet"
SUMMARY = PROJECT_ROOT / "data/quality/weather_drought_history.json"
MIN_EPISODE_DAYS = 14


def load_district_history() -> pd.DataFrame:
    locations = pd.read_csv(LOCATIONS)
    locations["latitude"] = (locations["latitude"] * 4).round() / 4
    locations["longitude"] = (locations["longitude"] * 4).round() / 4
    columns = [
        "valid_time",
        "latitude",
        "longitude",
        "precipitation_90d_sum",
        "soil_moisture_30d_mean",
        "water_balance_30d",
        "consecutive_dry_days",
    ]
    frames = []
    for path in sorted(FEATURE_ROOT.glob("year=*/features.parquet")):
        frame = pd.read_parquet(path, columns=columns)
        selected = frame.merge(
            locations[["state", "district", "latitude", "longitude"]],
            on=["latitude", "longitude"],
            how="inner",
            validate="many_to_many",
        )
        frames.append(selected)
    if not frames:
        raise FileNotFoundError(f"No historical feature partitions under {FEATURE_ROOT}")
    result = pd.concat(frames, ignore_index=True)
    result["valid_time"] = pd.to_datetime(result["valid_time"], utc=True).dt.normalize()
    return result.sort_values(["state", "district", "valid_time"])


def identify_dry_days(history: pd.DataFrame) -> pd.DataFrame:
    result = history.copy()
    result["month"] = result["valid_time"].dt.month
    group = result.groupby(["state", "district", "month"])
    for column in (
        "precipitation_90d_sum",
        "soil_moisture_30d_mean",
        "water_balance_30d",
    ):
        result[f"{column}_p20"] = group[column].transform(lambda values: values.quantile(0.20))
    result["drought_pattern_day"] = (
        result["precipitation_90d_sum"].le(result["precipitation_90d_sum_p20"])
        & (
            result["soil_moisture_30d_mean"].le(result["soil_moisture_30d_mean_p20"])
            | result["water_balance_30d"].le(result["water_balance_30d_p20"])
        )
        & result["consecutive_dry_days"].ge(7)
    )
    return result


def episodes_from_days(days: pd.DataFrame, *, minimum_days: int = MIN_EPISODE_DAYS) -> pd.DataFrame:
    records = []
    selected = days.loc[days["drought_pattern_day"]].copy()
    for (state, district), group in selected.groupby(["state", "district"]):
        group = group.sort_values("valid_time")
        group["episode_group"] = group["valid_time"].diff().dt.days.gt(7).cumsum()
        for _, episode in group.groupby("episode_group"):
            start = episode["valid_time"].min()
            end = episode["valid_time"].max()
            duration = int((end - start).days + 1)
            pattern_days = len(episode)
            if duration < minimum_days or pattern_days < minimum_days:
                continue
            records.append(
                {
                    "state": state,
                    "district": district,
                    "start_date": start,
                    "end_date": end,
                    "duration_days": duration,
                    "pattern_days": pattern_days,
                    "minimum_precipitation_90d_mm": float(episode["precipitation_90d_sum"].min()),
                    "minimum_soil_moisture": float(episode["soil_moisture_30d_mean"].min()),
                    "minimum_water_balance_30d_mm": float(episode["water_balance_30d"].min()),
                    "maximum_consecutive_dry_days": int(episode["consecutive_dry_days"].max()),
                    "source": "ERA5_GPM_WEATHER_DERIVED",
                    "label_method": "weather_pattern_episode",
                    "verified_disaster_event": False,
                }
            )
    return pd.DataFrame(records)


def build() -> dict:
    history = identify_dry_days(load_district_history())
    episodes = episodes_from_days(history)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".parquet.tmp")
    episodes.to_parquet(temporary, index=False, compression="snappy")
    os.replace(temporary, OUTPUT)
    summary = {
        "created_at": datetime.now(UTC).isoformat(),
        "episodes": len(episodes),
        "districts_with_episodes": int(episodes[["state", "district"]].drop_duplicates().shape[0]),
        "period": {
            "start": str(history["valid_time"].min().date()),
            "end": str(history["valid_time"].max().date()),
        },
        "minimum_episode_days": MIN_EPISODE_DAYS,
        "label_method": "weather_pattern_episode",
        "production_ground_truth": False,
        "output": str(OUTPUT),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "status"), nargs="?", default="build")
    arguments = parser.parse_args()
    if arguments.command == "build":
        result = build()
    else:
        if not SUMMARY.exists():
            raise SystemExit("Weather-derived drought history has not been built.")
        result = json.loads(SUMMARY.read_text(encoding="utf-8"))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
