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
from scripts.sources.common.config import PROJECT_ROOT
from scripts.susceptibility.static import STATIC_PATH

PROBABILITIES_PATH = PROJECT_ROOT / "data/serving/district_hazard_probabilities.parquet"
ASSESSMENT_PATH = PROJECT_ROOT / "data/serving/district_assessments.parquet"
MANIFEST_PATH = PROJECT_ROOT / "data/serving/district_assessment_manifest.json"


def _atomic_parquet(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    dataframe.to_parquet(temporary, index=False)
    os.replace(temporary, path)


def _level(score: float) -> str:
    if pd.isna(score):
        return "UNAVAILABLE"
    if score < 0.20:
        return "NONE"
    if score < 0.40:
        return "LOW"
    if score < 0.60:
        return "MODERATE"
    if score < 0.80:
        return "HIGH"
    return "EXTREME"


def _flood_signal(row: pd.Series) -> float:
    daily_rain = float(row["precipitation_sum_mm"]) / float(row["horizon_days"])
    rain_score = min(daily_rain / 50.0, 1.0)
    probability = float(row["precipitation_probability_max"]) / 100.0
    return round(0.75 * rain_score + 0.25 * probability, 4)


def _cyclone_signal(row: pd.Series) -> float:
    gust = float(row["wind_gust_max_kmh"])
    wind = float(row["wind_speed_max_kmh"])
    return round(min(max(gust / 90.0, wind / 65.0), 1.0), 4)


def _drought_signal(row: pd.Series) -> float:
    precipitation = float(row["precipitation_sum_mm"])
    et0 = max(float(row["et0_sum_mm"]), 0.1)
    return round(max(0.0, min(1.0, 1.0 - precipitation / et0)), 4)


def _mitigation(row: pd.Series) -> list[str]:
    actions = []
    if row["flood_forecast_signal"] >= 0.6:
        actions.extend(
            [
                "Keep drainage and culverts clear and monitor low-lying access routes.",
                "Follow district authority flood and evacuation advisories.",
            ]
        )
    if row["cyclone_forecast_signal"] >= 0.6:
        actions.extend(
            [
                "Secure loose roofing, equipment, and outdoor materials.",
                "Check official IMD cyclone bulletins before travel or field work.",
            ]
        )
    if row["drought_forecast_signal"] >= 0.6:
        actions.append("Review irrigation demand and conserve stored water.")
    if not actions:
        actions.append("Continue routine monitoring; no elevated short-range signal is present.")
    return actions


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
        dataframe["flood_forecast_signal"] = dataframe.apply(_flood_signal, axis=1)
        dataframe["cyclone_forecast_signal"] = dataframe.apply(_cyclone_signal, axis=1)
        dataframe["drought_forecast_signal"] = dataframe.apply(_drought_signal, axis=1)
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
            dataframe[f"{hazard}_land_risk_index"] = (
                dataframe[f"{hazard}_probability"]
                * dataframe[f"{hazard}_susceptibility"]
                * dataframe["land_exposure_score"]
            )
            dataframe[f"{hazard}_risk_level"] = dataframe[f"{hazard}_land_risk_index"].map(_level)
        dataframe["assessment_available"] = dataframe[
            ["flood_probability", "cyclone_probability"]
        ].notna().all(axis=1)
        dataframe["vulnerability_available"] = dataframe["social_vulnerability"].notna()
        dataframe["confidence_grade"] = np.where(
            dataframe["assessment_available"]
            & dataframe["district_wide_usable"].astype(bool)
            & dataframe["static_factor_coverage"].ge(0.8),
            "B",
            np.where(dataframe["assessment_available"], "C", "D"),
        )
        dataframe["confidence_reason"] = np.where(
            dataframe["assessment_available"],
            "Model probability available; confidence reduced by static-factor coverage.",
            "Forecast monitoring signal only; validated model probability is unavailable.",
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
            "scope": "land_hazard_only",
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
            "probability": None if pd.isna(probability) else float(probability),
            "susceptibility": float(row[f"{hazard}_susceptibility"]),
            "land_risk_index": None if pd.isna(risk_index) else float(risk_index),
            "risk_level": row[f"{hazard}_risk_level"],
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
        },
        "hazards": hazards,
        "mitigation_actions": json.loads(row["mitigation_actions"]),
        "disclaimer": (
            "Decision-support estimate, not an official warning. Follow IMD and local authorities."
        ),
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
