"""Build the static frontend data bundle from current serving artifacts."""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.serving.attribution import DISCLAIMER, RISK_SCALE, SOURCES
from scripts.serving.district_assessment import ASSESSMENT_PATH, MANIFEST_PATH
from scripts.serving.planning_outlook import HAZARDS, OUTLOOK_HORIZONS, build_planning_outlook
from scripts.sources.common.config import PROJECT_ROOT

BOUNDARIES_PATH = PROJECT_ROOT / "data/silver/geospatial/ne_district_boundaries.geojson"
BOUNDARY_SUMMARY_PATH = PROJECT_ROOT / "data/silver/geospatial/district_boundary_summary.json"
QUALITY_PATH = PROJECT_ROOT / "data/quality/vulnerability_calibration.json"
CHIRPS_PATH = PROJECT_ROOT / "data/quality/chirps_gpm_crosscheck.json"
OUTPUT_DIR = PROJECT_ROOT / "frontend/public/data"
PAYLOAD_PATH = OUTPUT_DIR / "susbiome-outlook.json"
FRONTEND_BOUNDARIES_PATH = OUTPUT_DIR / "ne-district-boundaries.geojson"


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return round(value, 4)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def _json_list(value: Any) -> list[str]:
    if value is None or pd.isna(value):
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return [str(value)]
    if isinstance(payload, list):
        return [str(item) for item in payload]
    return [str(payload)]


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _round_coordinates(value: Any) -> Any:
    if isinstance(value, list):
        if len(value) == 2 and all(isinstance(item, (int, float)) for item in value):
            return [round(float(value[0]), 5), round(float(value[1]), 5)]
        return [_round_coordinates(item) for item in value]
    return value


def _frontend_boundaries() -> dict:
    payload = _read_json(BOUNDARIES_PATH)
    features = []
    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        geometry = feature.get("geometry")
        if not geometry:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "state": properties.get("state"),
                    "district": properties.get("district"),
                    "boundary_status": properties.get("boundary_status"),
                },
                "geometry": {
                    "type": geometry.get("type"),
                    "coordinates": _round_coordinates(geometry.get("coordinates")),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def build(output_dir: Path = OUTPUT_DIR) -> dict:
    assessment = pd.read_parquet(ASSESSMENT_PATH)
    outlook = build_planning_outlook(assessment)
    latest = (
        assessment.sort_values(["state", "district", "horizon_days"])
        .loc[assessment["horizon_days"].eq(14)]
        .copy()
    )
    locations = latest.set_index(["state", "district"])
    states = sorted(outlook["state"].dropna().unique().tolist())

    districts = []
    for (state, district), row in locations.iterrows():
        districts.append(
            {
                "state": state,
                "district": district,
                "latitude": _clean(row.get("latitude_x", row.get("latitude_y"))),
                "longitude": _clean(row.get("longitude_x", row.get("longitude_y"))),
                "boundaryStatus": _clean(row.get("boundary_status")),
                "boundaryGrade": _clean(row.get("geographic_validation_grade")),
                "districtWideUsable": bool(row.get("district_wide_usable")),
                "staticCoverage": _clean(row.get("static_factor_coverage")),
                "dominantLandCover": _clean(row.get("dominant_land_cover_class")),
                "elevationMeanM": _clean(row.get("elevation_mean_m")),
                "slopeMeanDegrees": _clean(row.get("slope_mean_degrees")),
                "hydroclimateYears": _clean(row.get("hydroclimate_years")),
            }
        )

    records = []
    for _, row in outlook.iterrows():
        state = row["state"]
        district = row["district"]
        selected = locations.loc[(state, district)]
        hazards = {}
        for hazard in HAZARDS:
            hazards[hazard] = {
                "score": _clean(row[f"{hazard}_outlook_score"]),
                "level": _clean(row[f"{hazard}_outlook_level"]),
                "weatherRiskScore": _clean(selected.get(f"{hazard}_weather_risk_score")),
                "susceptibility": _clean(selected.get(f"{hazard}_susceptibility")),
                "probability": _clean(selected.get(f"{hazard}_probability")),
                "drivers": _json_list(selected.get(f"{hazard}_risk_drivers")),
            }
        records.append(
            {
                "state": state,
                "district": district,
                "horizon": int(row["outlook_horizon_days"]),
                "validFrom": str(row["valid_from"]),
                "validTo": str(row["valid_to"]),
                "compositeScore": _clean(row["composite_risk_score"]),
                "compositeLevel": _clean(row["composite_risk_level"]),
                "dominantHazard": _clean(row["dominant_hazard"]),
                "confidence": _clean(row["outlook_confidence"]),
                "forecastWeight": _clean(row["forecast_weight"]),
                "historicalWeight": _clean(row["historical_weight"]),
                "hazards": hazards,
                "forecast": {
                    "rainfallMm": _clean(selected.get("precipitation_sum_mm")),
                    "rainProbability": _clean(selected.get("precipitation_probability_max")),
                    "windGustKmh": _clean(selected.get("wind_gust_max_kmh")),
                    "windSpeedKmh": _clean(selected.get("wind_speed_max_kmh")),
                    "temperatureMaxC": _clean(selected.get("temperature_max_c")),
                    "temperatureMinC": _clean(selected.get("temperature_min_c")),
                    "et0Mm": _clean(selected.get("et0_sum_mm")),
                    "provider": _clean(selected.get("provider")),
                    "collectedAt": str(selected.get("collected_at")),
                },
                "quality": {
                    "staticCoverage": _clean(selected.get("static_factor_coverage")),
                    "confidenceGrade": _clean(selected.get("confidence_grade")),
                    "confidenceReason": _clean(selected.get("confidence_reason")),
                    "rainfallCrosscheck": _clean(selected.get("rainfall_crosscheck_status")),
                    "chirpsGpmCorrelation": _clean(selected.get("chirps_gpm_correlation")),
                    "assessmentMethod": _clean(selected.get("assessment_method")),
                    "scope": _clean(selected.get("assessment_scope")),
                },
                "actions": _json_list(selected.get("mitigation_actions")),
            }
        )

    manifest = _read_json(MANIFEST_PATH)
    boundary_summary = _read_json(BOUNDARY_SUMMARY_PATH)
    quality = _read_json(QUALITY_PATH)
    chirps = _read_json(CHIRPS_PATH)
    payload = {
        "meta": {
            "generatedAt": datetime.now(UTC).isoformat(),
            "assessmentGeneratedAt": manifest.get("generated_at"),
            "districts": len(districts),
            "states": len(states),
            "horizons": list(OUTLOOK_HORIZONS),
            "hazards": list(HAZARDS),
            "assessmentMethod": manifest.get("assessment_method"),
            "scope": "weather and physical land planning outlook",
            "outlookIsProbability": False,
            "disclaimer": DISCLAIMER,
            "riskScale": RISK_SCALE,
            "sources": SOURCES,
            "boundaryCoveragePercent": boundary_summary.get("coverage_percent"),
            "modelRelease": quality.get("release_id"),
            "modelStatuses": quality.get("hazards", {}),
            "rainfallCrosscheck": chirps,
        },
        "states": states,
        "districts": districts,
        "outlook": records,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    temporary = PAYLOAD_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, PAYLOAD_PATH)
    boundary_temporary = FRONTEND_BOUNDARIES_PATH.with_suffix(".geojson.tmp")
    boundary_temporary.write_text(
        json.dumps(_frontend_boundaries(), separators=(",", ":")), encoding="utf-8"
    )
    os.replace(boundary_temporary, FRONTEND_BOUNDARIES_PATH)
    return {
        "payload": str(PAYLOAD_PATH),
        "boundaries": str(FRONTEND_BOUNDARIES_PATH),
        "districts": len(districts),
        "outlook_rows": len(records),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    arguments = parser.parse_args()
    print(json.dumps(build(arguments.output_dir), indent=2))


if __name__ == "__main__":
    main()
