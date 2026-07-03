"""Extract conservative Northeast India cyclone labels from NOAA IBTrACS."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import xarray as xr

from scripts.sources.common.config import PROJECT_ROOT

URL = (
    "https://www.ncei.noaa.gov/data/international-best-track-archive-for-"
    "climate-stewardship-ibtracs/v04r01/access/netcdf/IBTrACS.NI.v04r01.nc"
)
RAW = PROJECT_ROOT / "data/bronze/events/ibtracs/IBTrACS.NI.v04r01.nc"
OUTPUT = PROJECT_ROOT / "data/bronze/ground_truth/ibtracs_ground_truth.parquet"
QUALITY_OUTPUT = PROJECT_ROOT / "data/quality/ibtracs_cyclone_provenance.json"
LOCATIONS = PROJECT_ROOT / "data/raw/locations.csv"
SOURCE_URL = (
    "https://www.ncei.noaa.gov/products/international-best-track-archive"
)
EARTH_RADIUS_KM = 6_371.0


def download(destination: Path = RAW) -> Path:
    if destination.exists() and destination.stat().st_size > 1_000_000:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(URL, timeout=180)
    response.raise_for_status()
    temporary = destination.with_suffix(".download")
    temporary.write_bytes(response.content)
    temporary.replace(destination)
    return destination


def _decode(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return str(value).strip()


def _distances(track_lat: np.ndarray, track_lon: np.ndarray, locations: pd.DataFrame) -> np.ndarray:
    latitude = np.radians(track_lat)[:, None]
    longitude = np.radians(track_lon)[:, None]
    location_latitude = np.radians(locations["latitude"].to_numpy())[None, :]
    location_longitude = np.radians(locations["longitude"].to_numpy())[None, :]
    delta_latitude = location_latitude - latitude
    delta_longitude = location_longitude - longitude
    value = (
        np.sin(delta_latitude / 2) ** 2
        + np.cos(latitude) * np.cos(location_latitude) * np.sin(delta_longitude / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(value))


def extract(
    source: Path = RAW,
    *,
    start_year: int = 2006,
    end_year: int = 2025,
    maximum_distance_km: float = 100.0,
    minimum_wind_knots: float = 34.0,
) -> pd.DataFrame:
    locations = pd.read_csv(LOCATIONS)
    records = []
    with xr.open_dataset(source) as dataset:
        seasons = dataset["season"].values
        storm_indexes = np.where((seasons >= start_year) & (seasons <= end_year))[0]
        for storm_index in storm_indexes:
            latitudes = dataset["lat"].isel(storm=storm_index).values.astype(float)
            longitudes = dataset["lon"].isel(storm=storm_index).values.astype(float)
            times = pd.to_datetime(
                dataset["time"].isel(storm=storm_index).values,
                utc=True,
                errors="coerce",
            )
            wind_sources = np.stack(
                [
                    dataset[name].isel(storm=storm_index).values.astype(float)
                    for name in ("wmo_wind", "newdelhi_wind", "usa_wind")
                ]
            )
            finite_wind = np.where(np.isfinite(wind_sources), wind_sources, -np.inf)
            winds = finite_wind.max(axis=0)
            agencies = np.asarray(["WMO", "IMD_NEW_DELHI", "USA"])
            selected_agencies = agencies[np.argmax(finite_wind, axis=0)]
            winds[winds == -np.inf] = np.nan
            valid = (
                np.isfinite(latitudes)
                & np.isfinite(longitudes)
                & np.isfinite(winds)
                & (winds >= minimum_wind_knots)
                & ~pd.isna(times)
            )
            if not valid.any():
                continue
            distances = _distances(latitudes[valid], longitudes[valid], locations)
            sid = _decode(dataset["sid"].isel(storm=storm_index).values.item())
            name = _decode(dataset["name"].isel(storm=storm_index).values.item()) or "UNNAMED"
            valid_times = times[valid]
            valid_winds = winds[valid]
            valid_agencies = selected_agencies[valid]
            valid_newdelhi_winds = wind_sources[1, valid]
            for location_index, location in locations.iterrows():
                point_index = int(np.argmin(distances[:, location_index]))
                distance = float(distances[point_index, location_index])
                if distance > maximum_distance_km:
                    continue
                wind = float(valid_winds[point_index])
                agency = str(valid_agencies[point_index])
                newdelhi_wind = float(valid_newdelhi_winds[point_index])
                severity = "EXTREME" if wind >= 96 else "SEVERE" if wind >= 64 else "MODERATE"
                records.append(
                    {
                        "schema_version": "1.0",
                        "event_id": f"IBTRACS_{sid}_{location.state}_{location.district}".replace(" ", "_"),
                        "source": "IBTRACS",
                        "source_event_id": sid,
                        "event_date": valid_times[point_index].normalize(),
                        "hazard_type": "CYCLONE",
                        "hazard_subtype": "TROPICAL_CYCLONE",
                        "severity": severity,
                        "country": "India",
                        "state": location.state,
                        "district": location.district,
                        "admin_level": "DISTRICT",
                        "latitude": float(location.latitude),
                        "longitude": float(location.longitude),
                        "location_source": "DISTRICT",
                        "headline": f"IBTrACS cyclone {name} near {location.district}",
                        "description": (
                            f"Observed cyclone track passed {distance:.1f} km from the "
                            f"district centroid with {wind:.0f} kt reported wind."
                        ),
                        "source_name": (
                            "NOAA NCEI IBTrACS v04r01 with IMD New Delhi agency wind"
                            if agency == "IMD_NEW_DELHI"
                            else "NOAA NCEI IBTrACS v04r01"
                        ),
                        "source_url": SOURCE_URL,
                        "confidence": 95.0,
                        "verified": True,
                        "collected_at": datetime.now(UTC),
                        "distance_km": round(distance, 2),
                        "wind_knots": wind,
                        "wind_agency": agency,
                        "imd_newdelhi_wind_knots": (
                            newdelhi_wind if np.isfinite(newdelhi_wind) else np.nan
                        ),
                        "imd_observation_available": bool(np.isfinite(newdelhi_wind)),
                    }
                )
    result = pd.DataFrame(records)
    if not result.empty:
        result = result.drop_duplicates(["source_event_id", "state", "district"])
        result = result.sort_values(["event_date", "state", "district"]).reset_index(drop=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2006)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--maximum-distance-km", type=float, default=100.0)
    arguments = parser.parse_args()
    source = download()
    result = extract(
        source,
        start_year=arguments.start_year,
        end_year=arguments.end_year,
        maximum_distance_km=arguments.maximum_distance_km,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUTPUT, index=False, compression="snappy")
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "records": len(result),
        "storms": result["source_event_id"].nunique() if not result.empty else 0,
        "states": result["state"].value_counts().to_dict() if not result.empty else {},
        "wind_agencies": result["wind_agency"].value_counts().to_dict() if not result.empty else {},
        "imd_observation_records": int(result["imd_observation_available"].sum()) if not result.empty else 0,
        "source": "NOAA IBTrACS v04r01 including IMD New Delhi agency observations",
        "output": str(OUTPUT),
    }
    QUALITY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
