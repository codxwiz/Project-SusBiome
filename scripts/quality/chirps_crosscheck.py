"""Collect compact CHIRPS point histories and cross-check fused GPM rainfall."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import xarray as xr

from scripts.sources.common.config import PROJECT_ROOT

URL = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/netcdf/p25/chirps-v2.0.{year}.days_p25.nc"
LOCATIONS = PROJECT_ROOT / "data/raw/locations.csv"
BRONZE = PROJECT_ROOT / "data/bronze/chirps"
SILVER = PROJECT_ROOT / "data/silver/validation/chirps"
FUSION = PROJECT_ROOT / "data/fusion/historical"
REPORT = PROJECT_ROOT / "data/quality/chirps_gpm_crosscheck.json"
DISTRICT_SUMMARY = PROJECT_ROOT / "data/quality/chirps_gpm_district_summary.parquet"
DEFAULT_START = 2021
DEFAULT_END = 2024


def _download(year: int, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".nc.tmp")
    with requests.get(URL.format(year=year), stream=True, timeout=180) as response:
        response.raise_for_status()
        with temporary.open("wb") as output:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    output.write(chunk)
    os.replace(temporary, destination)


def collect_year(year: int, *, keep_raw: bool = False) -> Path:
    output = SILVER / f"year={year:04d}" / "district_daily.parquet"
    if output.exists() and output.stat().st_size:
        return output
    source = BRONZE / f"chirps-v2.0.{year}.days_p25.nc"
    if not source.exists():
        _download(year, source)
    locations = pd.read_csv(LOCATIONS)
    with xr.open_dataset(source) as dataset:
        variable = "precip" if "precip" in dataset else "precipitation"
        rows = []
        for location in locations.itertuples(index=False):
            values = dataset[variable].sel(
                latitude=float(location.latitude),
                longitude=float(location.longitude),
                method="nearest",
            )
            frame = values.to_dataframe(name="chirps_precipitation_mm").reset_index()
            frame["state"] = location.state
            frame["district"] = location.district
            rows.append(frame[["state", "district", "time", "chirps_precipitation_mm"]])
    result = pd.concat(rows, ignore_index=True).rename(columns={"time": "valid_date"})
    result["valid_date"] = pd.to_datetime(result["valid_date"]).dt.normalize()
    result["chirps_precipitation_mm"] = pd.to_numeric(
        result["chirps_precipitation_mm"], errors="coerce"
    ).clip(lower=0)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".parquet.tmp")
    result.to_parquet(temporary, index=False, compression="snappy")
    os.replace(temporary, output)
    if not keep_raw:
        source.unlink(missing_ok=True)
    return output


def comparison_metrics(frame: pd.DataFrame) -> dict:
    valid = frame[["chirps_precipitation_mm", "gpm_precipitation_mm"]].dropna()
    if valid.empty:
        return {"days": 0, "correlation": None, "mean_absolute_error_mm": None, "bias_mm": None}
    difference = valid["gpm_precipitation_mm"] - valid["chirps_precipitation_mm"]
    correlation = valid["gpm_precipitation_mm"].corr(valid["chirps_precipitation_mm"])
    return {
        "days": len(valid),
        "correlation": None if pd.isna(correlation) else float(correlation),
        "mean_absolute_error_mm": float(difference.abs().mean()),
        "bias_mm": float(difference.mean()),
        "gpm_total_mm": float(valid["gpm_precipitation_mm"].sum()),
        "chirps_total_mm": float(valid["chirps_precipitation_mm"].sum()),
    }


def _fusion_district_daily(year: int) -> pd.DataFrame:
    path = FUSION / f"year={year:04d}" / "weather.parquet"
    frame = pd.read_parquet(path, columns=["valid_time", "latitude", "longitude", "precipitation"])
    locations = pd.read_csv(LOCATIONS)
    locations["latitude"] = (locations["latitude"] * 4).round() / 4
    locations["longitude"] = (locations["longitude"] * 4).round() / 4
    selected = frame.merge(
        locations[["state", "district", "latitude", "longitude"]],
        on=["latitude", "longitude"],
        how="inner",
        validate="many_to_many",
    )
    selected["valid_date"] = pd.to_datetime(selected["valid_time"], utc=True).dt.tz_localize(None).dt.normalize()
    return selected.rename(columns={"precipitation": "gpm_precipitation_mm"})[
        ["state", "district", "valid_date", "gpm_precipitation_mm"]
    ]


def crosscheck(start_year: int, end_year: int) -> dict:
    summaries = []
    for year in range(start_year, end_year + 1):
        chirps = pd.read_parquet(collect_year(year))
        merged = chirps.merge(
            _fusion_district_daily(year),
            on=["state", "district", "valid_date"],
            how="inner",
            validate="one_to_one",
        )
        for (state, district), group in merged.groupby(["state", "district"]):
            summaries.append(
                {"year": year, "state": state, "district": district, **comparison_metrics(group)}
            )
    metrics = pd.DataFrame(summaries)
    detail = PROJECT_ROOT / "data/quality/chirps_gpm_district_year.parquet"
    metrics.to_parquet(detail, index=False)
    district_summary = (
        metrics.groupby(["state", "district"], as_index=False)
        .agg(
            chirps_gpm_correlation=("correlation", "median"),
            chirps_gpm_mae_mm=("mean_absolute_error_mm", "median"),
            chirps_gpm_bias_mm=("bias_mm", "median"),
            chirps_years_compared=("year", "nunique"),
        )
    )
    district_summary.to_parquet(DISTRICT_SUMMARY, index=False)
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "source": "CHIRPS v2.0 daily 0.25 degree",
        "years": list(range(start_year, end_year + 1)),
        "district_years": len(metrics),
        "districts": int(metrics[["state", "district"]].drop_duplicates().shape[0]),
        "median_daily_correlation": float(metrics["correlation"].median()),
        "median_daily_mae_mm": float(metrics["mean_absolute_error_mm"].median()),
        "median_daily_bias_mm": float(metrics["bias_mm"].median()),
        "detail": str(detail),
        "district_summary": str(DISTRICT_SUMMARY),
        "interpretation": "Independent rainfall cross-check only; CHIRPS does not replace GPM in live scoring.",
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("collect", "crosscheck", "all", "status"), nargs="?", default="all")
    parser.add_argument("--start-year", type=int, default=DEFAULT_START)
    parser.add_argument("--end-year", type=int, default=DEFAULT_END)
    parser.add_argument("--keep-raw", action="store_true")
    arguments = parser.parse_args()
    if arguments.start_year > arguments.end_year:
        raise SystemExit("--start-year must not exceed --end-year")
    if arguments.command == "status":
        if not REPORT.exists():
            raise SystemExit("CHIRPS cross-check has not been built.")
        result = json.loads(REPORT.read_text(encoding="utf-8"))
    elif arguments.command == "collect":
        result = {
            str(year): str(collect_year(year, keep_raw=arguments.keep_raw))
            for year in range(arguments.start_year, arguments.end_year + 1)
        }
    else:
        result = crosscheck(arguments.start_year, arguments.end_year)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
