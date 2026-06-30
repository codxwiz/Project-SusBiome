"""Fuse partitioned ERA5 and GPM daily observations by analysis grid and year."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from scripts.sources.common.config import PROJECT_ROOT

ERA5_ROOT = PROJECT_ROOT / "data/silver/weather/era5"
GPM_ROOT = PROJECT_ROOT / "data/silver/weather/gpm"
OUTPUT_ROOT = PROJECT_ROOT / "data/fusion/historical"

KEYS = ["valid_time", "latitude", "longitude"]


def read_year(root: Path, year: int) -> pd.DataFrame:
    files = sorted((root / f"year={year:04d}").glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No partitions for {year} under {root}")
    return pd.concat((pd.read_parquet(path) for path in files), ignore_index=True)


def fuse_frames(era5: pd.DataFrame, gpm: pd.DataFrame) -> pd.DataFrame:
    for frame in (era5, gpm):
        frame["valid_time"] = pd.to_datetime(frame["valid_time"], utc=True).dt.normalize()
        frame["latitude"] = (pd.to_numeric(frame["latitude"]) / 0.25).round() * 0.25
        frame["longitude"] = (pd.to_numeric(frame["longitude"]) / 0.25).round() * 0.25
    era5 = era5.drop_duplicates(KEYS)
    gpm = gpm.groupby(KEYS, as_index=False)["precipitation_gpm"].mean()
    fused = era5.merge(gpm, on=KEYS, how="left", validate="one_to_one")
    fused["precipitation_source"] = "ERA5"
    fused.loc[fused["precipitation_gpm"].notna(), "precipitation_source"] = "GPM"
    fused["precipitation"] = fused["precipitation_gpm"].combine_first(
        fused["precipitation_era5"]
    )
    fused = fused.drop(columns=["precipitation_gpm", "precipitation_era5"])
    fused["value"] = fused.get("value", fused["temperature"])
    fused = fused.sort_values(KEYS).reset_index(drop=True)
    if fused.empty:
        raise ValueError("No ERA5 observations were available for fusion.")
    if fused.isna().any().any():
        missing = int(fused.isna().sum().sum())
        raise ValueError(f"Fused historical data contains {missing} null values.")
    return fused


def fuse_year(year: int, *, output_root: Path = OUTPUT_ROOT) -> Path:
    fused = fuse_frames(read_year(ERA5_ROOT, year), read_year(GPM_ROOT, year))
    observed_days = fused["valid_time"].dt.normalize().nunique()
    expected_days = 366 if pd.Timestamp(year, 12, 31).is_leap_year else 365
    if observed_days < expected_days * 0.95:
        raise ValueError(
            f"Year {year} has only {observed_days}/{expected_days} overlapping days."
        )
    destination = output_root / f"year={year:04d}" / "weather.parquet"
    destination.parent.mkdir(parents=True, exist_ok=True)
    fused.to_parquet(destination, index=False, compression="snappy")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2006)
    parser.add_argument("--end-year", type=int, default=2025)
    arguments = parser.parse_args()
    report = {"completed": [], "failed": {}}
    for year in range(arguments.start_year, arguments.end_year + 1):
        try:
            report["completed"].append(str(fuse_year(year)))
        except Exception as error:
            report["failed"][str(year)] = str(error)
    print(json.dumps(report, indent=2))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
