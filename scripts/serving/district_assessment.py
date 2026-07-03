"""Build explainable district forecast signals and production risk contracts."""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.forecast.open_meteo import HORIZONS_PATH
from scripts.serving.attribution import DISCLAIMER, RISK_SCALE, SOURCES
from scripts.sources.common.config import PROJECT_ROOT
from scripts.susceptibility.static import STATIC_PATH

PROBABILITIES_PATH = PROJECT_ROOT / "data/serving/district_hazard_probabilities.parquet"
ASSESSMENT_PATH = PROJECT_ROOT / "data/serving/district_assessments.parquet"
MANIFEST_PATH = PROJECT_ROOT / "data/serving/district_assessment_manifest.json"
IMD_CYCLONE_PATH = PROJECT_ROOT / "data/silver/alerts/imd_cyclone.json"
CHIRPS_SUMMARY_PATH = PROJECT_ROOT / "data/quality/chirps_gpm_district_summary.parquet"


def _atomic_parquet(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    dataframe.to_parquet(temporary, index=False)
    os.replace(temporary, path)


ASSESSMENT_METHOD = "weather_land_index_v2"
MAX_FORECAST_AGE_HOURS = 36


class AssessmentUnavailableError(RuntimeError):
    """Serving assessment cannot be used safely for a current response."""


def load_current_assessment(
    path: str | Path = ASSESSMENT_PATH,
    *,
    now: datetime | None = None,
    max_age_hours: int = MAX_FORECAST_AGE_HOURS,
) -> pd.DataFrame:
    """Load serving data and reject stale or incomplete forecast artifacts."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"District serving dataset is not available: {source}")
    dataframe = pd.read_parquet(source)
    if dataframe.empty or "collected_at" not in dataframe:
        raise AssessmentUnavailableError(
            "District serving dataset has no forecast collection timestamp."
        )
    collected = pd.to_datetime(dataframe["collected_at"], utc=True, errors="coerce").max()
    if pd.isna(collected):
        raise AssessmentUnavailableError(
            "District serving dataset has an invalid forecast collection timestamp."
        )
    current = now or datetime.now(UTC)
    age_hours = (current - collected.to_pydatetime()).total_seconds() / 3600
    if age_hours > max_age_hours:
        raise AssessmentUnavailableError(
            f"District forecast is stale ({age_hours:.1f} hours; maximum {max_age_hours} hours)."
        )
    return dataframe


def _level(score: float) -> str:
    if pd.isna(score):
        return "UNAVAILABLE"
    if score < 25:
        return "LOW"
    if score < 50:
        return "MODERATE"
    if score < 75:
        return "HIGH"
    return "VERY HIGH"


def _flood_signal(row: pd.Series) -> float:
    horizon_scale = float(row["horizon_days"]) / 7.0
    extreme_rainfall = max(float(row["precipitation_7d_p95"]) * horizon_scale, 20.0)
    rain_score = min(float(row["precipitation_sum_mm"]) / extreme_rainfall, 1.0)
    probability = float(row["precipitation_probability_max"]) / 100.0
    return round(0.80 * rain_score + 0.20 * probability, 4)


def _cyclone_signal(row: pd.Series) -> float:
    gust = float(row["wind_gust_max_kmh"])
    wind = float(row["wind_speed_max_kmh"])
    wind_score = min(max(gust / 90.0, wind / 65.0), 1.0)
    rain_score = min(float(row["precipitation_sum_mm"]) / 150.0, 1.0)
    return round(0.80 * wind_score + 0.20 * rain_score, 4)


def _drought_signal(row: pd.Series) -> float:
    precipitation = float(row["precipitation_sum_mm"])
    et0 = max(float(row["et0_sum_mm"]), 0.1)
    return round(max(0.0, min(1.0, 1.0 - precipitation / et0)), 4)


def _mitigation(row: pd.Series) -> list[str]:
    actions = []
    if row["flood_weather_risk_score"] >= 60:
        actions.extend(
            [
                "Keep drainage and culverts clear and monitor low-lying access routes.",
                "Follow district authority flood and evacuation advisories.",
            ]
        )
    if row["cyclone_weather_risk_score"] >= 60:
        actions.extend(
            [
                "Secure loose roofing, equipment, and outdoor materials.",
                "Check official IMD cyclone bulletins before travel or field work.",
            ]
        )
    if row["drought_weather_risk_score"] >= 60:
        actions.append("Review irrigation demand and conserve stored water.")
    if not actions:
        actions.append("Continue routine monitoring; no elevated short-range signal is present.")
    return actions


def _drivers(row: pd.Series, hazard: str) -> list[str]:
    if hazard == "flood":
        return [
            f"Forecast rainfall: {float(row['precipitation_sum_mm']):.1f} mm",
            f"Maximum rain probability: {float(row['precipitation_probability_max']):.0f}%",
            "District rainfall, runoff, soil wetness, SRTM terrain, and WorldCover context",
        ]
    if hazard == "cyclone":
        return [
            f"Maximum wind gust: {float(row['wind_gust_max_kmh']):.1f} km/h",
            f"Maximum sustained wind signal: {float(row['wind_speed_max_kmh']):.1f} km/h",
            "Forecast rainfall, district wind history, and WorldCover context",
            f"IMD bulletin confirmation: {row.get('cyclone_confirmation_status', 'UNAVAILABLE')}",
        ]
    return [
        f"Forecast rainfall: {float(row['precipitation_sum_mm']):.1f} mm",
        f"Forecast evapotranspiration: {float(row['et0_sum_mm']):.1f} mm",
        "District dry-spell, water-balance history, and WorldCover context",
    ]


class DistrictAssessmentBuilder:
    @staticmethod
    def _load_probabilities(path: Path) -> pd.DataFrame | None:
        if not path.exists():
            return None
        probabilities = pd.read_parquet(path)
        required = {
            "state", "district", "horizon_days", "flood_probability", "cyclone_probability"
        }
        missing = required - set(probabilities.columns)
        if missing:
            raise ValueError("Probability dataset is missing: " + ", ".join(sorted(missing)))
        for column in ("flood_probability", "cyclone_probability"):
            values = pd.to_numeric(probabilities[column], errors="coerce")
            if values.isna().any() or not values.between(0, 1).all():
                raise ValueError(f"{column} must contain values from 0 to 1.")
        return probabilities

    def build(
        self,
        output_path: str | Path = ASSESSMENT_PATH,
        probabilities_path: str | Path = PROBABILITIES_PATH,
    ) -> dict:
        forecasts = pd.read_parquet(HORIZONS_PATH)
        static = pd.read_parquet(STATIC_PATH)
        dataframe = forecasts.merge(static, on=["state", "district"], how="left", validate="many_to_one")
        if CHIRPS_SUMMARY_PATH.exists():
            rainfall_validation = pd.read_parquet(CHIRPS_SUMMARY_PATH)
            dataframe = dataframe.merge(
                rainfall_validation,
                on=["state", "district"],
                how="left",
                validate="many_to_one",
            )
            dataframe["rainfall_crosscheck_status"] = "AVAILABLE"
        else:
            dataframe["chirps_gpm_correlation"] = np.nan
            dataframe["chirps_gpm_mae_mm"] = np.nan
            dataframe["chirps_gpm_bias_mm"] = np.nan
            dataframe["chirps_years_compared"] = 0
            dataframe["rainfall_crosscheck_status"] = "UNAVAILABLE"
        dataframe["flood_forecast_signal"] = dataframe.apply(_flood_signal, axis=1)
        dataframe["cyclone_forecast_signal"] = dataframe.apply(_cyclone_signal, axis=1)
        dataframe["drought_forecast_signal"] = dataframe.apply(_drought_signal, axis=1)
        if IMD_CYCLONE_PATH.exists():
            confirmation = json.loads(IMD_CYCLONE_PATH.read_text(encoding="utf-8"))
            dataframe["cyclone_confirmation_status"] = confirmation.get("status", "UNAVAILABLE")
            dataframe["cyclone_confirmation_url"] = confirmation.get("source_url")
            dataframe["cyclone_confirmation_collected_at"] = confirmation.get("collected_at")
        else:
            dataframe["cyclone_confirmation_status"] = "UNAVAILABLE"
            dataframe["cyclone_confirmation_url"] = None
            dataframe["cyclone_confirmation_collected_at"] = None
        probabilities = self._load_probabilities(Path(probabilities_path))
        if probabilities is not None:
            keep = [
                column for column in probabilities.columns
                if column not in {"latitude", "longitude", "valid_from", "valid_to"}
            ]
            dataframe = dataframe.merge(
                probabilities[keep], on=["state", "district", "horizon_days"],
                how="left", validate="one_to_one",
            )
        else:
            dataframe["flood_probability"] = np.nan
            dataframe["cyclone_probability"] = np.nan
            dataframe["drought_probability"] = np.nan
            dataframe["model_version"] = None
        dataframe["land_exposure_score"] = 1.0
        dataframe["exposure_mode"] = "land_only_neutral"
        for hazard in ("flood", "cyclone", "drought"):
            dataframe[f"{hazard}_weather_risk_score"] = (
                100
                * (
                    0.85 * dataframe[f"{hazard}_forecast_signal"]
                    + 0.15 * dataframe[f"{hazard}_susceptibility"]
                )
            ).clip(0, 100).round(1)
            dataframe[f"{hazard}_land_risk_index"] = (
                dataframe[f"{hazard}_weather_risk_score"] / 100.0
            )
            dataframe[f"{hazard}_risk_level"] = dataframe[
                f"{hazard}_weather_risk_score"
            ].map(_level)
            dataframe[f"{hazard}_risk_drivers"] = dataframe.apply(
                lambda row, selected=hazard: json.dumps(_drivers(row, selected)), axis=1
            )
        dataframe["assessment_available"] = dataframe[
            [
                "flood_weather_risk_score",
                "cyclone_weather_risk_score",
                "drought_weather_risk_score",
            ]
        ].notna().all(axis=1)
        dataframe["vulnerability_available"] = dataframe["social_vulnerability"].notna()
        dataframe["assessment_method"] = ASSESSMENT_METHOD
        dataframe["assessment_scope"] = "district_weather_land_susceptibility_outlook"
        dataframe["confidence_grade"] = np.where(
            dataframe["assessment_available"]
            & dataframe["district_wide_usable"].astype(bool)
            & dataframe["geographic_validation_grade"].isin(["A", "B"])
            & dataframe["hydroclimate_years"].ge(20)
            & dataframe["static_factor_coverage"].ge(0.8),
            "B",
            np.where(dataframe["assessment_available"], "C", "D"),
        )
        dataframe["confidence_reason"] = np.where(
            dataframe["district_wide_usable"].astype(bool),
            "Complete weather and land inputs; index is not a calibrated disaster probability.",
            "Current forecast and district point history; district-wide polygon unavailable.",
        )
        dataframe["mitigation_actions"] = dataframe.apply(
            lambda row: json.dumps(_mitigation(row)), axis=1
        )
        dataframe["generated_at"] = datetime.now(UTC).isoformat()
        _atomic_parquet(dataframe, Path(output_path))
        manifest = {
            "generated_at": dataframe["generated_at"].iloc[0],
            "districts": int(dataframe[["state", "district"]].drop_duplicates().shape[0]),
            "rows": len(dataframe),
            "horizons": sorted(dataframe["horizon_days"].unique().astype(int).tolist()),
            "model_probabilities_available": probabilities is not None,
            "assessment_rows_available": int(dataframe["assessment_available"].sum()),
            "forecast_signal_rows": len(dataframe),
            "assessment_method": ASSESSMENT_METHOD,
            "scope": "district_weather_land_susceptibility_outlook",
            "output": str(Path(output_path)),
        }
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest


def district_report(row: pd.Series) -> dict:
    """Convert one assessment record into a stable API/dashboard report."""
    hazards = {}
    for hazard in ("flood", "cyclone", "drought"):
        probability = row.get(f"{hazard}_probability")
        risk_index = row.get(f"{hazard}_land_risk_index")
        hazards[hazard] = {
            "forecast_signal": float(row[f"{hazard}_forecast_signal"]),
            "weather_risk_score": float(row[f"{hazard}_weather_risk_score"]),
            "probability": None if pd.isna(probability) else float(probability),
            "susceptibility": float(row[f"{hazard}_susceptibility"]),
            "land_risk_index": None if pd.isna(risk_index) else float(risk_index),
            "risk_level": row[f"{hazard}_risk_level"],
            "drivers": json.loads(row[f"{hazard}_risk_drivers"]),
        }
    return {
        "state": row["state"],
        "district": row["district"],
        "horizon_days": int(row["horizon_days"]),
        "valid_from": str(row["valid_from"]),
        "valid_to": str(row["valid_to"]),
        "assessment_available": bool(row["assessment_available"]),
        "vulnerability_available": bool(row["vulnerability_available"]),
        "assessment_scope": row["assessment_scope"],
        "assessment_method": row["assessment_method"],
        "confidence": {
            "grade": row["confidence_grade"],
            "reason": row["confidence_reason"],
            "static_factor_coverage": float(row["static_factor_coverage"]),
            "boundary_status": row["boundary_status"],
        },
        "forecast": {
            "precipitation_sum_mm": float(row["precipitation_sum_mm"]),
            "precipitation_probability_max": float(row["precipitation_probability_max"]),
            "wind_gust_max_kmh": float(row["wind_gust_max_kmh"]),
            "temperature_max_c": float(row["temperature_max_c"]),
            "temperature_min_c": float(row["temperature_min_c"]),
            "provider": row["provider"],
            "spatial_support": row["spatial_support"],
            "collected_at": str(row.get("collected_at")),
        },
        "data_freshness": {
            "forecast_collected_at": str(row.get("collected_at")),
            "assessment_generated_at": str(row.get("generated_at")),
            "maximum_forecast_age_hours": MAX_FORECAST_AGE_HOURS,
        },
        "physical_land_context": {
            "elevation_mean_m": (
                None if pd.isna(row.get("elevation_mean_m")) else float(row["elevation_mean_m"])
            ),
            "slope_mean_degrees": (
                None
                if pd.isna(row.get("slope_mean_degrees"))
                else float(row["slope_mean_degrees"])
            ),
            "dominant_land_cover": row.get("dominant_land_cover_class"),
            "terrain_sample_count": int(row.get("terrain_sample_count", 0) or 0),
            "land_cover_sample_count": int(row.get("land_cover_sample_count", 0) or 0),
            "terrain_spatial_support": row.get("terrain_spatial_support"),
            "land_cover_spatial_support": row.get("land_cover_spatial_support"),
        },
        "official_alerts": {
            "cyclone": {
                "status": row.get("cyclone_confirmation_status", "UNAVAILABLE"),
                "source": "India Meteorological Department RSMC New Delhi",
                "url": row.get("cyclone_confirmation_url"),
                "collected_at": row.get("cyclone_confirmation_collected_at"),
            }
        },
        "rainfall_crosscheck": {
            "status": row.get("rainfall_crosscheck_status", "UNAVAILABLE"),
            "years_compared": int(row.get("chirps_years_compared", 0) or 0),
            "daily_correlation": (
                None
                if pd.isna(row.get("chirps_gpm_correlation"))
                else float(row["chirps_gpm_correlation"])
            ),
            "median_daily_mae_mm": (
                None
                if pd.isna(row.get("chirps_gpm_mae_mm"))
                else float(row["chirps_gpm_mae_mm"])
            ),
            "median_daily_bias_mm": (
                None
                if pd.isna(row.get("chirps_gpm_bias_mm"))
                else float(row["chirps_gpm_bias_mm"])
            ),
        },
        "hazards": hazards,
        "mitigation_actions": json.loads(row["mitigation_actions"]),
        "sources": SOURCES,
        "risk_scale": RISK_SCALE,
        "disclaimer": DISCLAIMER,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "status"), nargs="?", default="build")
    arguments = parser.parse_args()
    if arguments.command == "build":
        result = DistrictAssessmentBuilder().build()
    else:
        if not MANIFEST_PATH.exists():
            raise SystemExit("Assessment manifest does not exist.")
        result = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
