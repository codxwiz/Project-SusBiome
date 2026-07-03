"""Collect terrain samples and build explainable static susceptibility factors."""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from scripts.geospatial.districts import (
    BOUNDARIES_PATH,
    MANIFEST_PATH,
    geometry_bbox,
    point_in_geometry,
)
from scripts.sources.common.config import PROJECT_ROOT
from scripts.susceptibility.land_context import (
    CONTEXT_MANIFEST_PATH,
    LAND_COVER_PATH,
    SRTMTerrainCollector,
    WorldCoverCollector,
)

GROUND_TRUTH_PATH = PROJECT_ROOT / "data/gold/ground_truth.parquet"
TERRAIN_PATH = PROJECT_ROOT / "data/silver/susceptibility/terrain.parquet"
STATIC_PATH = PROJECT_ROOT / "data/silver/susceptibility/district_static.parquet"
HYDROCLIMATE_PATH = PROJECT_ROOT / "data/silver/susceptibility/hydroclimate.parquet"
DROUGHT_HISTORY_PATH = PROJECT_ROOT / "data/silver/events/weather_drought_episodes.parquet"
SUMMARY_PATH = PROJECT_ROOT / "data/silver/susceptibility/summary.json"
HISTORICAL_FEATURE_ROOT = PROJECT_ROOT / "data/gold/features_historical"
ELEVATION_ENDPOINT = "https://api.open-meteo.com/v1/elevation"


def _atomic_parquet(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    dataframe.to_parquet(temporary, index=False)
    os.replace(temporary, path)


def _normalize(series: pd.Series, *, invert: bool = False) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    valid = values.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=series.index)
    low, high = valid.quantile([0.05, 0.95])
    if math.isclose(float(low), float(high)):
        result = pd.Series(0.5, index=series.index)
    else:
        result = ((values - low) / (high - low)).clip(0, 1)
    return 1 - result if invert else result


def _polygon_samples(geometry: dict, count: int = 3) -> list[tuple[float, float]]:
    minimum_x, minimum_y, maximum_x, maximum_y = geometry_bbox(geometry)
    samples = []
    for latitude in np.linspace(minimum_y, maximum_y, count + 2)[1:-1]:
        for longitude in np.linspace(minimum_x, maximum_x, count + 2)[1:-1]:
            if point_in_geometry(float(longitude), float(latitude), geometry):
                samples.append((float(latitude), float(longitude)))
    return samples


class TerrainCollector:
    def __init__(self, session: requests.Session | None = None, batch_size: int = 50) -> None:
        self.session = session or requests.Session()
        self.batch_size = batch_size

    def _elevations(self, points: list[tuple[float, float]]) -> list[float]:
        results: list[float] = []
        for start in range(0, len(points), self.batch_size):
            batch = points[start : start + self.batch_size]
            params = {
                "latitude": ",".join(str(point[0]) for point in batch),
                "longitude": ",".join(str(point[1]) for point in batch),
            }
            error: Exception | None = None
            for attempt in range(6):
                try:
                    response = self.session.get(ELEVATION_ENDPOINT, params=params, timeout=90)
                    if response.status_code == 429:
                        retry_after = min(float(response.headers.get("Retry-After", 15)), 60)
                        time.sleep(retry_after)
                        continue
                    response.raise_for_status()
                    elevations = response.json().get("elevation", [])
                    if len(elevations) != len(batch):
                        raise ValueError("Elevation response length mismatch.")
                    results.extend(float(value) for value in elevations)
                    error = None
                    time.sleep(1.0)
                    break
                except (requests.RequestException, ValueError) as caught:
                    error = caught
                    if attempt < 5:
                        time.sleep(min(2**attempt, 30))
            if error is not None:
                raise RuntimeError(f"Elevation provider failed after retries: {error}") from error
        return results

    def collect(self, output_path: str | Path = TERRAIN_PATH) -> dict:
        manifest = pd.read_csv(MANIFEST_PATH)
        boundary_payload = json.loads(BOUNDARIES_PATH.read_text(encoding="utf-8"))
        geometries = {
            (feature["properties"]["state"], feature["properties"]["district"]): feature["geometry"]
            for feature in boundary_payload["features"]
        }
        records = []
        all_points: list[tuple[float, float]] = []
        for row in manifest.itertuples(index=False):
            geometry = geometries.get((row.state, row.district))
            points = _polygon_samples(geometry) if geometry else []
            support = "district_polygon_samples"
            if not points:
                points = [(float(row.latitude), float(row.longitude))]
                support = "representative_point"
            start = len(all_points)
            all_points.extend(points)
            records.append((row, support, start, len(all_points)))
        elevations = self._elevations(all_points)
        collected_at = datetime.now(UTC).isoformat()
        rows = []
        for row, support, start, end in records:
            values = np.asarray(elevations[start:end], dtype=float)
            rows.append(
                {
                    "state": row.state,
                    "district": row.district,
                    "elevation_mean_m": round(float(values.mean()), 2),
                    "elevation_min_m": round(float(values.min()), 2),
                    "elevation_max_m": round(float(values.max()), 2),
                    "terrain_relief_m": round(float(values.max() - values.min()), 2),
                    "terrain_sample_count": len(values),
                    "terrain_spatial_support": support,
                    "terrain_source": "Open-Meteo Elevation API 90m DEM",
                    "terrain_collected_at": collected_at,
                }
            )
        terrain = pd.DataFrame(rows)
        _atomic_parquet(terrain, Path(output_path))
        return {
            "collected_at": collected_at,
            "districts": len(terrain),
            "polygon_sampled": int(
                terrain["terrain_spatial_support"].eq("district_polygon_samples").sum()
            ),
            "representative_only": int(
                terrain["terrain_spatial_support"].eq("representative_point").sum()
            ),
            "sample_points": len(all_points),
            "output": str(Path(output_path)),
        }


class StaticSusceptibilityBuilder:
    @staticmethod
    def historical_hydroclimate(output_path: str | Path = HYDROCLIMATE_PATH) -> pd.DataFrame:
        """Summarize stable climate normals without loading the full archive at once."""
        annual = []
        columns = [
            "latitude", "longitude", "precipitation_7d_sum", "runoff_7d_sum",
            "soil_moisture_30d_mean", "wind_speed_7d_max", "consecutive_dry_days",
            "water_balance_30d",
        ]
        for path in sorted(HISTORICAL_FEATURE_ROOT.glob("year=*/features.parquet")):
            frame = pd.read_parquet(path, columns=columns)
            grouped = frame.groupby(["latitude", "longitude"], as_index=False)
            means = grouped[
                [
                    "runoff_7d_sum", "soil_moisture_30d_mean", "wind_speed_7d_max",
                    "consecutive_dry_days", "water_balance_30d",
                ]
            ].mean()
            precipitation = grouped["precipitation_7d_sum"].quantile(0.95).rename(
                columns={"precipitation_7d_sum": "precipitation_7d_p95"}
            )
            annual.append(means.merge(precipitation, on=["latitude", "longitude"]))
        if not annual:
            raise FileNotFoundError(f"No historical feature partitions under {HISTORICAL_FEATURE_ROOT}")
        hydroclimate = (
            pd.concat(annual, ignore_index=True)
            .groupby(["latitude", "longitude"], as_index=False)
            .mean(numeric_only=True)
        )
        hydroclimate = hydroclimate.rename(
            columns={
                "runoff_7d_sum": "runoff_7d_climatology",
                "soil_moisture_30d_mean": "soil_moisture_climatology",
                "wind_speed_7d_max": "wind_speed_7d_climatology",
                "consecutive_dry_days": "dry_spell_climatology",
                "water_balance_30d": "water_balance_climatology",
            }
        )
        hydroclimate["hydroclimate_years"] = len(annual)
        hydroclimate["hydroclimate_source"] = "ERA5 and NASA GPM historical archive"
        hydroclimate["hydroclimate_generated_at"] = datetime.now(UTC).isoformat()
        _atomic_parquet(hydroclimate, Path(output_path))
        return hydroclimate

    @staticmethod
    def historical_frequency() -> pd.DataFrame:
        events = pd.read_parquet(GROUND_TRUTH_PATH)
        events = events.loc[events["verified"].fillna(False)].copy()
        events["hazard_type"] = events["hazard_type"].astype(str).str.upper()
        independent = events.drop_duplicates(
            ["state", "district", "hazard_type", "source", "source_event_id"]
        )
        counts = (
            independent.groupby(["state", "district", "hazard_type"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
        for hazard in ("FLOOD", "DROUGHT", "CYCLONE"):
            if hazard not in counts:
                counts[hazard] = 0
        return counts.rename(
            columns={
                "FLOOD": "flood_independent_events",
                "DROUGHT": "drought_independent_events",
                "CYCLONE": "cyclone_independent_events",
            }
        )

    def build(self, output_path: str | Path = STATIC_PATH) -> dict:
        manifest = pd.read_csv(MANIFEST_PATH)
        terrain = pd.read_parquet(TERRAIN_PATH)
        dataframe = manifest.merge(terrain, on=["state", "district"], how="left")
        if LAND_COVER_PATH.exists():
            land_cover = pd.read_parquet(LAND_COVER_PATH)
            dataframe = dataframe.merge(
                land_cover, on=["state", "district"], how="left", validate="one_to_one"
            )
        else:
            dataframe["land_cover_sample_count"] = 0
            for hazard in ("flood", "cyclone", "drought"):
                dataframe[f"{hazard}_land_cover_score"] = np.nan
        dataframe = dataframe.merge(self.historical_frequency(), on=["state", "district"], how="left")
        if DROUGHT_HISTORY_PATH.exists():
            drought_episodes = pd.read_parquet(DROUGHT_HISTORY_PATH)
            drought_counts = (
                drought_episodes.groupby(["state", "district"]).size().rename("drought_weather_episodes").reset_index()
            )
            dataframe = dataframe.merge(drought_counts, on=["state", "district"], how="left")
        else:
            dataframe["drought_weather_episodes"] = 0
        dataframe["drought_weather_episodes"] = dataframe["drought_weather_episodes"].fillna(0).astype(int)
        hydroclimate = self.historical_hydroclimate()
        dataframe["grid_latitude"] = (dataframe["latitude"] * 4).round() / 4
        dataframe["grid_longitude"] = (dataframe["longitude"] * 4).round() / 4
        dataframe = dataframe.merge(
            hydroclimate,
            left_on=["grid_latitude", "grid_longitude"],
            right_on=["latitude", "longitude"],
            how="left",
            suffixes=("", "_grid"),
            validate="many_to_one",
        )
        event_columns = [
            "flood_independent_events", "drought_independent_events", "cyclone_independent_events"
        ]
        dataframe[event_columns] = dataframe[event_columns].fillna(0).astype(int)
        dataframe["low_elevation_score"] = _normalize(dataframe["elevation_mean_m"], invert=True)
        dataframe["terrain_relief_score"] = _normalize(dataframe["terrain_relief_m"])
        dataframe["low_slope_score"] = _normalize(
            dataframe.get("slope_mean_degrees", pd.Series(np.nan, index=dataframe.index)),
            invert=True,
        )
        dataframe["extreme_rainfall_score"] = _normalize(dataframe["precipitation_7d_p95"])
        dataframe["runoff_climatology_score"] = _normalize(dataframe["runoff_7d_climatology"])
        dataframe["soil_wetness_score"] = _normalize(dataframe["soil_moisture_climatology"])
        dataframe["wind_climatology_score"] = _normalize(dataframe["wind_speed_7d_climatology"])
        dataframe["dry_spell_score"] = _normalize(dataframe["dry_spell_climatology"])
        dataframe["water_deficit_score"] = _normalize(
            dataframe["water_balance_climatology"], invert=True
        )
        dataframe["drought_episode_score"] = _normalize(dataframe["drought_weather_episodes"])
        for hazard in ("flood", "drought", "cyclone"):
            dataframe[f"{hazard}_history_score"] = _normalize(
                dataframe[f"{hazard}_independent_events"]
            )
        dataframe["flood_susceptibility"] = (
            0.15 * dataframe["low_elevation_score"]
            + 0.05 * dataframe["terrain_relief_score"]
            + 0.10 * dataframe["low_slope_score"].fillna(0.5)
            + 0.15 * dataframe["flood_land_cover_score"].fillna(0.5)
            + 0.15 * dataframe["flood_history_score"]
            + 0.15 * dataframe["extreme_rainfall_score"]
            + 0.15 * dataframe["runoff_climatology_score"]
            + 0.10 * dataframe["soil_wetness_score"]
        ).clip(0, 1)
        dataframe["cyclone_susceptibility"] = (
            0.10 * dataframe["low_elevation_score"]
            + 0.15 * dataframe["cyclone_land_cover_score"].fillna(0.5)
            + 0.45 * dataframe["cyclone_history_score"]
            + 0.30 * dataframe["wind_climatology_score"]
        ).clip(0, 1)
        dataframe["drought_susceptibility"] = (
            0.15 * dataframe["drought_land_cover_score"].fillna(0.5)
            + 0.2125 * dataframe["drought_history_score"]
            + 0.2125 * dataframe["dry_spell_score"]
            + 0.2125 * dataframe["water_deficit_score"]
            + 0.2125 * dataframe["drought_episode_score"]
        ).clip(0, 1)
        dataframe["river_factor"] = np.nan
        dataframe["land_cover_factor"] = dataframe[
            ["flood_land_cover_score", "cyclone_land_cover_score", "drought_land_cover_score"]
        ].mean(axis=1)
        dataframe["soil_factor"] = np.nan
        dataframe["social_vulnerability"] = np.nan
        coverage = (
            dataframe["elevation_mean_m"].notna().astype(float)
            + dataframe["precipitation_7d_p95"].notna().astype(float)
            + dataframe[event_columns].notna().all(axis=1).astype(float)
            + dataframe["drought_weather_episodes"].notna().astype(float)
            + dataframe["land_cover_sample_count"].fillna(0).gt(0).astype(float)
        ) / 5.0
        dataframe["static_factor_coverage"] = coverage
        dataframe["static_confidence_grade"] = np.where(
            dataframe["district_wide_usable"].astype(bool) & coverage.ge(0.8),
            "B",
            np.where(dataframe["district_wide_usable"].astype(bool), "C", "D"),
        )
        dataframe["assessment_scope"] = "land_hazard_only"
        dataframe["generated_at"] = datetime.now(UTC).isoformat()
        _atomic_parquet(dataframe, Path(output_path))
        summary = {
            "generated_at": dataframe["generated_at"].iloc[0],
            "districts": len(dataframe),
            "polygon_supported": int(dataframe["district_wide_usable"].sum()),
            "confidence_grades": dataframe["static_confidence_grade"].value_counts().to_dict(),
            "available_factors": [
                "terrain",
                "slope",
                "land_cover",
                "verified_historical_hazard_frequency",
                "hydroclimate_normals",
                "weather_derived_drought_history",
            ],
            "missing_factors": ["rivers", "soil", "social_vulnerability"],
            "scope": "weather_hazard_outlook; not a population or asset vulnerability estimate",
            "output": str(Path(output_path)),
        }
        SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("terrain", "land-cover", "build", "all", "status"),
        default="all",
        nargs="?",
    )
    arguments = parser.parse_args()
    result: dict = {}
    if arguments.command in {"terrain", "all"}:
        result["terrain"] = SRTMTerrainCollector().collect()
    if arguments.command in {"land-cover", "all"}:
        result["land_cover"] = WorldCoverCollector().collect()
    if arguments.command in {"build", "all"}:
        result["static"] = StaticSusceptibilityBuilder().build()
    if arguments.command == "status":
        if not SUMMARY_PATH.exists():
            raise SystemExit("Susceptibility summary does not exist.")
        result = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    context = {key: value for key, value in result.items() if key in {"terrain", "land_cover"}}
    if context:
        CONTEXT_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONTEXT_MANIFEST_PATH.write_text(json.dumps(context, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
