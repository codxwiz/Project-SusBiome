"""Collect conservative Northeast India flood and drought labels from GDACS."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from time import sleep

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ground_truth.collectors.collect_ibtracs import _distances
from scripts.fusion.models import NORTHEAST_INDIA_BOUNDS
from scripts.sources.common.config import PROJECT_ROOT

API_ROOT = "https://www.gdacs.org/gdacsapi/api"
SEARCH_URL = f"{API_ROOT}/events/geteventlist/SEARCH"
GEOMETRY_URL = f"{API_ROOT}/polygons/getgeometry"
OUTPUT = PROJECT_ROOT / "data/bronze/ground_truth/gdacs_ground_truth.parquet"
CACHE = PROJECT_ROOT / "data/bronze/events/gdacs"
LOCATIONS = PROJECT_ROOT / "data/raw/locations.csv"
PAGE_SIZE = 100


def _session() -> requests.Session:
    retry = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.headers["User-Agent"] = "SusBiome research collector/1.0"
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _get_json(
    session: requests.Session,
    url: str,
    params: dict,
    cache_path: Path,
    *,
    refresh: bool,
) -> dict:
    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    response = session.get(url, params=params, timeout=90)
    response.raise_for_status()
    payload = response.json()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    temporary.replace(cache_path)
    return payload


def fetch(
    event_type: str,
    start_year: int,
    end_year: int,
    *,
    refresh: bool = False,
    maximum_pages: int = 100,
) -> list[dict]:
    features: list[dict] = []
    session = _session()
    previous_ids: tuple[str, ...] | None = None
    for page in range(1, maximum_pages + 1):
        cache_path = CACHE / (
            f"{event_type}_{start_year}_{end_year}_page_{page:03d}.json"
        )
        payload = _get_json(
            session,
            SEARCH_URL,
            {
                "eventlist": event_type,
                "fromdate": f"{start_year}-01-01",
                "todate": f"{end_year}-12-31",
                "alertlevel": "red;orange;green",
                "country": "India",
                "pagesize": PAGE_SIZE,
                "pagenumber": page,
            },
            cache_path,
            refresh=refresh,
        )
        batch = payload.get("features", [])
        identifiers = tuple(
            str((item.get("properties") or {}).get("eventid")) for item in batch
        )
        if identifiers == previous_ids:
            break
        features.extend(batch)
        print(f"GDACS {event_type}: page={page}, records={len(batch)}", flush=True)
        if len(batch) < PAGE_SIZE:
            break
        previous_ids = identifiers
        sleep(0.2)
    else:
        raise RuntimeError(f"GDACS {event_type} exceeded {maximum_pages} pages")
    return features


def _ring_contains(longitude: float, latitude: float, ring: list[list[float]]) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous[:2]
        x2, y2 = current[:2]
        crosses = (y1 > latitude) != (y2 > latitude)
        if crosses and longitude < (x2 - x1) * (latitude - y1) / (y2 - y1) + x1:
            inside = not inside
        previous = current
    return inside


def _geometry_contains(geometry: dict, longitude: float, latitude: float) -> bool:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    polygons = [coordinates] if geometry_type == "Polygon" else coordinates
    if geometry_type not in {"Polygon", "MultiPolygon"}:
        return False
    for polygon in polygons:
        if polygon and _ring_contains(longitude, latitude, polygon[0]):
            if not any(_ring_contains(longitude, latitude, hole) for hole in polygon[1:]):
                return True
    return False


def _base_record(
    properties: dict,
    location: pd.Series,
    event_date: pd.Timestamp,
    hazard: str,
    description: str,
    collected_at: datetime,
) -> dict:
    event_id = str(properties["eventid"])
    alert = str(properties.get("alertlevel") or "Green").upper()
    severity = "SEVERE" if alert == "RED" else "MODERATE" if alert == "ORANGE" else "MINOR"
    subtype = "RIVER_FLOOD" if hazard == "FLOOD" else "METEOROLOGICAL_DROUGHT"
    return {
        "schema_version": "1.0",
        "event_id": f"GDACS_{hazard}_{event_id}_{location['state']}_{location['district']}".replace(" ", "_"),
        "source": "GDACS",
        "source_event_id": event_id,
        "event_date": event_date.normalize(),
        "hazard_type": hazard,
        "hazard_subtype": subtype,
        "severity": severity,
        "country": "India",
        "state": location["state"],
        "district": location["district"],
        "admin_level": "DISTRICT",
        "latitude": float(location["latitude"]),
        "longitude": float(location["longitude"]),
        "location_source": "DISTRICT",
        "headline": properties.get("name") or f"GDACS {hazard.lower()} in India",
        "description": description,
        "source_name": "Global Disaster Alert and Coordination System (GDACS)",
        "source_url": f"https://www.gdacs.org/report.aspx?eventid={event_id}&eventtype={properties['eventtype']}",
        "confidence": 90.0,
        "verified": True,
        "collected_at": collected_at,
        "alert_level": alert,
    }


def _valid_event(feature: dict, start_year: int, end_year: int) -> tuple[dict, pd.Timestamp] | None:
    properties = feature.get("properties") or {}
    event_date = pd.to_datetime(properties.get("fromdate"), utc=True, errors="coerce")
    if (
        not properties.get("eventid")
        or str(properties.get("istemporary", "false")).lower() == "true"
        or pd.isna(event_date)
        or not start_year <= event_date.year <= end_year
    ):
        return None
    return properties, event_date


def extract_floods(
    features: list[dict],
    locations: pd.DataFrame,
    *,
    start_year: int,
    end_year: int,
    maximum_distance_km: float = 125.0,
) -> list[dict]:
    bounds = NORTHEAST_INDIA_BOUNDS
    records: list[dict] = []
    seen: set[str] = set()
    collected_at = datetime.now(UTC)
    for feature in features:
        valid = _valid_event(feature, start_year, end_year)
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if not valid or geometry.get("type") != "Point" or len(coordinates) < 2:
            continue
        properties, event_date = valid
        event_id = str(properties["eventid"])
        longitude, latitude = map(float, coordinates[:2])
        if event_id in seen or not (
            bounds["min_latitude"] <= latitude <= bounds["max_latitude"]
            and bounds["min_longitude"] <= longitude <= bounds["max_longitude"]
        ):
            continue
        distances = _distances(np.array([latitude]), np.array([longitude]), locations)[0]
        index = int(np.argmin(distances))
        distance = float(distances[index])
        if distance > maximum_distance_km:
            continue
        location = locations.iloc[index]
        records.append(
            _base_record(
                properties,
                location,
                event_date,
                "FLOOD",
                f"GDACS flood centroid was {distance:.1f} km from the {location['district']} district centroid.",
                collected_at,
            )
        )
        records[-1]["distance_km"] = round(distance, 2)
        seen.add(event_id)
    return records


def extract_droughts(
    features: list[dict],
    locations: pd.DataFrame,
    *,
    start_year: int,
    end_year: int,
    refresh: bool = False,
) -> list[dict]:
    records: list[dict] = []
    seen: set[str] = set()
    session = _session()
    collected_at = datetime.now(UTC)
    for feature in features:
        valid = _valid_event(feature, start_year, end_year)
        if not valid:
            continue
        properties, event_date = valid
        event_id = str(properties["eventid"])
        if event_id in seen:
            continue
        seen.add(event_id)
        episode_id = properties.get("episodeid") or 1
        payload = _get_json(
            session,
            GEOMETRY_URL,
            {"eventtype": "DR", "eventid": event_id, "episodeid": episode_id},
            CACHE / f"DR_{event_id}_{episode_id}_geometry.json",
            refresh=refresh,
        )
        geometries = [
            item.get("geometry") or {}
            for item in payload.get("features", [])
            if (item.get("geometry") or {}).get("type") in {"Polygon", "MultiPolygon"}
        ]
        for _, location in locations.iterrows():
            if any(
                _geometry_contains(geometry, float(location.longitude), float(location.latitude))
                for geometry in geometries
            ):
                records.append(
                    _base_record(
                        properties,
                        location,
                        event_date,
                        "DROUGHT",
                        f"The {location['district']} district centroid falls inside the GDACS drought affected-area polygon.",
                        collected_at,
                    )
                )
        sleep(0.1)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2006)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--maximum-distance-km", type=float, default=125.0)
    parser.add_argument("--refresh", action="store_true")
    arguments = parser.parse_args()
    locations = pd.read_csv(LOCATIONS)
    flood_features = fetch("FL", arguments.start_year, arguments.end_year, refresh=arguments.refresh)
    drought_features = fetch("DR", arguments.start_year, arguments.end_year, refresh=arguments.refresh)
    records = extract_floods(
        flood_features,
        locations,
        start_year=arguments.start_year,
        end_year=arguments.end_year,
        maximum_distance_km=arguments.maximum_distance_km,
    )
    records.extend(
        extract_droughts(
            drought_features,
            locations,
            start_year=arguments.start_year,
            end_year=arguments.end_year,
            refresh=arguments.refresh,
        )
    )
    result = pd.DataFrame(records)
    if not result.empty:
        result = result.drop_duplicates(["source_event_id", "hazard_type", "state", "district"])
        result = result.sort_values(["event_date", "hazard_type", "state", "district"])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp.parquet")
    result.to_parquet(temporary, index=False, compression="snappy")
    temporary.replace(OUTPUT)
    print(
        {
            "records": len(result),
            "hazards": result["hazard_type"].value_counts().to_dict() if not result.empty else {},
            "states": result["state"].value_counts().to_dict() if not result.empty else {},
            "output": str(OUTPUT),
        }
    )


if __name__ == "__main__":
    main()
