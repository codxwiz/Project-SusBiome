"""Build a coordinate-based land context assessment from cached production artifacts."""

from __future__ import annotations

import json
import math
import zipfile
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from scripts.fusion.models import NORTHEAST_INDIA_BOUNDS
from scripts.geospatial.districts import BOUNDARIES_PATH, MANIFEST_PATH, point_in_geometry
from scripts.serving.district_assessment import (
    ASSESSMENT_PATH,
    _level,
    _weather_land_score,
    district_report,
    load_current_assessment,
)
from scripts.susceptibility.land_context import (
    CYCLONE_CLASS_SCORE,
    DROUGHT_CLASS_SCORE,
    FLOOD_CLASS_SCORE,
    SRTM_ROOT,
    WORLDCOVER_ROOT,
    WORLD_COVER_CLASSES,
    SRTMTerrainCollector,
    srtm_tile,
    worldcover_tile,
)


def _haversine_km(left_lat: float, left_lon: float, right_lat: float, right_lon: float) -> float:
    radius = 6_371.0
    left_latitude, right_latitude = map(math.radians, (left_lat, right_lat))
    delta_latitude = right_latitude - left_latitude
    delta_longitude = math.radians(right_lon - left_lon)
    value = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(left_latitude) * math.cos(right_latitude) * math.sin(delta_longitude / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(value))


def locate_district(latitude: float, longitude: float) -> dict:
    bounds = NORTHEAST_INDIA_BOUNDS
    if not (
        bounds["min_latitude"] <= latitude <= bounds["max_latitude"]
        and bounds["min_longitude"] <= longitude <= bounds["max_longitude"]
    ):
        raise ValueError("Coordinates are outside the Northeast India service area.")
    boundaries = json.loads(BOUNDARIES_PATH.read_text(encoding="utf-8"))
    for feature in boundaries["features"]:
        if point_in_geometry(longitude, latitude, feature["geometry"]):
            return {
                "state": feature["properties"]["state"],
                "district": feature["properties"]["district"],
                "match_method": "district_polygon",
                "distance_km": 0.0,
            }
    locations = pd.read_csv(MANIFEST_PATH)
    distances = locations.apply(
        lambda row: _haversine_km(
            latitude, longitude, float(row["latitude"]), float(row["longitude"])
        ),
        axis=1,
    )
    nearest = locations.loc[distances.idxmin()]
    distance = float(distances.min())
    if distance > 40:
        raise ValueError("Coordinates could not be matched to a supported district.")
    return {
        "state": nearest["state"],
        "district": nearest["district"],
        "match_method": "nearest_representative_point",
        "distance_km": round(distance, 2),
    }


@lru_cache(maxsize=4)
def _load_srtm_array(path: str) -> np.ndarray:
    source = Path(path)
    with zipfile.ZipFile(source) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".hgt")]
        if len(members) != 1:
            raise ValueError(f"Expected one HGT member in {source}")
        payload = archive.read(members[0])
    side = int(math.sqrt(len(payload) / 2))
    return np.frombuffer(payload, dtype=">i2").reshape(side, side)


def _srtm_context(latitude: float, longitude: float) -> dict | None:
    tile = srtm_tile(latitude, longitude)
    path = SRTM_ROOT / f"{tile}.SRTMGL1.hgt.zip"
    if not path.exists():
        return None
    array = _load_srtm_array(str(path))
    elevation, slope = SRTMTerrainCollector._sample(array, latitude, longitude)
    if not np.isfinite(elevation) or not np.isfinite(slope):
        return None
    return {
        "elevation_m": round(elevation, 1),
        "slope_degrees": round(slope, 2),
        "source": "NASA SRTMGL1 v003",
        "resolution_m": 30,
    }


def _worldcover_context(latitude: float, longitude: float) -> dict | None:
    tile = worldcover_tile(latitude, longitude)
    path = WORLDCOVER_ROOT / f"ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
    if not path.exists():
        return None
    with rasterio.open(path) as dataset:
        value = int(next(dataset.sample([(longitude, latitude)]))[0])
    if value not in WORLD_COVER_CLASSES:
        return None
    return {
        "class_code": value,
        "class_name": WORLD_COVER_CLASSES[value],
        "source": "ESA WorldCover 2021 v200",
        "resolution_m": 10,
    }


def _point_factor(hazard: str, terrain: dict | None, land_cover: dict | None) -> float | None:
    values: list[tuple[float, float]] = []
    if land_cover:
        mapping = {
            "flood": FLOOD_CLASS_SCORE,
            "cyclone": CYCLONE_CLASS_SCORE,
            "drought": DROUGHT_CLASS_SCORE,
        }[hazard]
        values.append((mapping[land_cover["class_code"]], 0.6))
    if terrain and hazard == "flood":
        low_elevation = 1 - min(max(terrain["elevation_m"] / 1_500.0, 0.0), 1.0)
        low_slope = 1 - min(max(terrain["slope_degrees"] / 30.0, 0.0), 1.0)
        values.extend([(low_elevation, 0.25), (low_slope, 0.15)])
    if not values:
        return None
    total_weight = sum(weight for _, weight in values)
    return sum(value * weight for value, weight in values) / total_weight


def location_report(latitude: float, longitude: float, horizon_days: int = 7) -> dict:
    if horizon_days not in {3, 7, 14}:
        raise ValueError("Forecast horizon must be 3, 7, or 14 days.")
    match = locate_district(latitude, longitude)
    assessment = load_current_assessment(ASSESSMENT_PATH)
    selected = assessment.loc[
        assessment["state"].eq(match["state"])
        & assessment["district"].eq(match["district"])
        & assessment["horizon_days"].eq(horizon_days)
    ]
    if selected.empty:
        raise ValueError("No current assessment is available for the matched district.")
    row = selected.iloc[0]
    terrain = _srtm_context(latitude, longitude)
    land_cover = _worldcover_context(latitude, longitude)
    hazards = {}
    for hazard in ("flood", "cyclone", "drought"):
        point_factor = _point_factor(hazard, terrain, land_cover)
        district_susceptibility = float(row[f"{hazard}_susceptibility"])
        location_susceptibility = (
            district_susceptibility
            if point_factor is None
            else 0.70 * district_susceptibility + 0.30 * point_factor
        )
        score = round(_weather_land_score(row, hazard, location_susceptibility), 1)
        probability = row.get(f"{hazard}_probability")
        hazards[hazard] = {
            "weather_land_risk_score": score,
            "risk_level": _level(score),
            "district_susceptibility": round(district_susceptibility, 4),
            "location_susceptibility": round(location_susceptibility, 4),
            "point_factor_available": point_factor is not None,
            "probability": None if pd.isna(probability) else float(probability),
        }
    context_available = terrain is not None and land_cover is not None
    return {
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "district_match": match,
        "horizon_days": horizon_days,
        "assessment_scope": "coordinate_weather_and_land_susceptibility_outlook",
        "assessment_method": "location_weather_land_index_v1",
        "context_available": context_available,
        "confidence": {
            "grade": "B" if context_available and match["match_method"] == "district_polygon" else "C",
            "reason": (
                "Current forecast combined with district history, 30 m terrain, and 10 m land cover."
                if context_available
                else "District weather assessment used; one or more point land factors are unavailable."
            ),
        },
        "land_context": {"terrain": terrain, "land_cover": land_cover},
        "hazards": hazards,
        "district_assessment": district_report(row),
    }
