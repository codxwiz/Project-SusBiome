"""Validate, reconcile, and aggregate Northeast India district geometries."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd
import requests

from scripts.sources.common.config import PROJECT_ROOT

LOCATIONS_PATH = PROJECT_ROOT / "data/raw/locations.csv"
SOURCE_PATH = PROJECT_ROOT / "data/raw/geospatial/geoBoundaries-IND-ADM2.geojson"
BOUNDARIES_PATH = PROJECT_ROOT / "data/silver/geospatial/ne_district_boundaries.geojson"
MANIFEST_PATH = PROJECT_ROOT / "data/silver/geospatial/district_boundary_manifest.csv"
SUMMARY_PATH = PROJECT_ROOT / "data/silver/geospatial/district_boundary_summary.json"

SOURCE = {
    "provider": "geoBoundaries gbOpen",
    "boundary_id": "IND-ADM2-76128533",
    "boundary_year": 2021,
    "source": "Pathways Data Pvt. Ltd., lgdirectory.gov.in",
    "license": "ODbL 1.0",
    "download_url": (
        "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/"
        "gbOpen/IND/ADM2/geoBoundaries-IND-ADM2_simplified.geojson"
    ),
    "artifact_url": (
        "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/"
        "releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2_simplified.geojson"
    ),
    "sha256": "d68db39cd3e2d0892af268e2b0454166368ce3b5b8a78fcda63069ec92a641db",
}


def normalize_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    text = re.sub(r"\b(district|dist)\b", " ", text.lower())
    return re.sub(r"[^a-z0-9]+", "", text)


def _rings(geometry: dict) -> Iterator[list[list[float]]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geometry_type == "Polygon":
        yield from coordinates
    elif geometry_type == "MultiPolygon":
        for polygon in coordinates:
            yield from polygon


def geometry_bbox(geometry: dict) -> tuple[float, float, float, float]:
    points = [point for ring in _rings(geometry) for point in ring]
    if not points:
        raise ValueError("Geometry has no coordinates.")
    longitudes = [float(point[0]) for point in points]
    latitudes = [float(point[1]) for point in points]
    return min(longitudes), min(latitudes), max(longitudes), max(latitudes)


def _point_in_ring(longitude: float, latitude: float, ring: list[list[float]]) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = float(previous[0]), float(previous[1])
        x2, y2 = float(current[0]), float(current[1])
        if min(y1, y2) <= latitude <= max(y1, y2) and min(x1, x2) <= longitude <= max(x1, x2):
            cross = (x2 - x1) * (latitude - y1) - (y2 - y1) * (longitude - x1)
            if abs(cross) < 1e-10:
                return True
        intersects = (y1 > latitude) != (y2 > latitude)
        if intersects:
            crossing_x = (x2 - x1) * (latitude - y1) / (y2 - y1) + x1
            if longitude < crossing_x:
                inside = not inside
        previous = current
    return inside


def point_in_geometry(longitude: float, latitude: float, geometry: dict) -> bool:
    minimum_x, minimum_y, maximum_x, maximum_y = geometry_bbox(geometry)
    if not (minimum_x <= longitude <= maximum_x and minimum_y <= latitude <= maximum_y):
        return False
    polygons = (
        [geometry.get("coordinates", [])]
        if geometry.get("type") == "Polygon"
        else geometry.get("coordinates", [])
    )
    for polygon in polygons:
        if polygon and _point_in_ring(longitude, latitude, polygon[0]):
            if not any(_point_in_ring(longitude, latitude, hole) for hole in polygon[1:]):
                return True
    return False


def _similarity(left: str, right: str) -> float:
    from difflib import SequenceMatcher

    return SequenceMatcher(None, normalize_name(left), normalize_name(right)).ratio()


@dataclass(slots=True)
class BoundaryMatch:
    state: str
    district: str
    latitude: float
    longitude: float
    source_name: str | None
    source_id: str | None
    status: str
    similarity: float
    geometry: dict | None


class DistrictBoundaryRegistry:
    """Canonical bridge between the current district list and source geometries."""

    def __init__(
        self,
        source_path: str | Path = SOURCE_PATH,
        locations_path: str | Path = LOCATIONS_PATH,
    ) -> None:
        self.source_path = Path(source_path)
        self.locations_path = Path(locations_path)

    def load_source(self) -> list[dict]:
        if not self.source_path.exists():
            raise FileNotFoundError(
                f"Boundary source is missing: {self.source_path}. Run the boundary collector first."
            )
        payload = json.loads(self.source_path.read_text(encoding="utf-8"))
        if payload.get("type") != "FeatureCollection":
            raise ValueError("Boundary source must be a GeoJSON FeatureCollection.")
        features = payload.get("features", [])
        if not features:
            raise ValueError("Boundary source contains no features.")
        return features

    def download(self, session: requests.Session | None = None) -> dict:
        """Download the pinned boundary artifact and verify its checksum."""
        session = session or requests.Session()
        self.source_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.source_path.with_suffix(".geojson.tmp")
        try:
            with session.get(SOURCE["artifact_url"], stream=True, timeout=180) as response:
                response.raise_for_status()
                with temporary.open("wb") as destination:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            destination.write(chunk)
            checksum = hashlib.sha256(temporary.read_bytes()).hexdigest()
            if checksum != SOURCE["sha256"]:
                raise ValueError(f"Boundary checksum mismatch: {checksum}")
            temporary.replace(self.source_path)
        finally:
            temporary.unlink(missing_ok=True)
        return {"path": str(self.source_path), "sha256": SOURCE["sha256"]}

    def load_locations(self) -> pd.DataFrame:
        locations = pd.read_csv(self.locations_path)
        required = {"state", "district", "latitude", "longitude"}
        missing = required - set(locations.columns)
        if missing:
            raise ValueError("Location registry is missing: " + ", ".join(sorted(missing)))
        if locations.duplicated(["state", "district"]).any():
            raise ValueError("Location registry contains duplicate districts.")
        return locations.sort_values(["state", "district"]).reset_index(drop=True)

    def reconcile(self) -> list[BoundaryMatch]:
        features = self.load_source()
        by_normalized_name: dict[str, list[dict]] = {}
        for feature in features:
            name = normalize_name(feature["properties"]["shapeName"])
            by_normalized_name.setdefault(name, []).append(feature)
        matches: list[BoundaryMatch] = []
        for row in self.load_locations().itertuples(index=False):
            exact_candidates = by_normalized_name.get(normalize_name(row.district), [])
            nearby_exact = [
                feature
                for feature in exact_candidates
                if 87.0 <= geometry_bbox(feature["geometry"])[0] <= 98.0
                and 20.0 <= geometry_bbox(feature["geometry"])[1] <= 30.0
            ]
            containing = nearby_exact or [
                feature for feature in features
                if point_in_geometry(float(row.longitude), float(row.latitude), feature["geometry"])
            ]
            if not containing:
                matches.append(
                    BoundaryMatch(
                        row.state, row.district, row.latitude, row.longitude,
                        None, None, "unresolved", 0.0, None,
                    )
                )
                continue
            feature = max(
                containing,
                key=lambda item: _similarity(row.district, item["properties"]["shapeName"]),
            )
            source_name = str(feature["properties"]["shapeName"])
            similarity = _similarity(row.district, source_name)
            if nearby_exact or normalize_name(row.district) == normalize_name(source_name):
                status = "exact"
            elif similarity >= 0.76:
                status = "fuzzy"
            else:
                status = "legacy_parent"
            matches.append(
                BoundaryMatch(
                    row.state,
                    row.district,
                    float(row.latitude),
                    float(row.longitude),
                    source_name,
                    str(feature["properties"].get("shapeID", "")),
                    status,
                    round(similarity, 4),
                    feature["geometry"] if status in {"exact", "fuzzy"} else None,
                )
            )
        by_source: dict[str, list[BoundaryMatch]] = {}
        for match in matches:
            if match.source_id and match.geometry is not None:
                by_source.setdefault(match.source_id, []).append(match)
        for duplicate_matches in by_source.values():
            if len(duplicate_matches) < 2:
                continue
            exact = [match for match in duplicate_matches if match.status == "exact"]
            keeper = exact[0] if exact else max(duplicate_matches, key=lambda item: item.similarity)
            for match in duplicate_matches:
                if match is not keeper:
                    match.status = "legacy_parent"
                    match.geometry = None
        return matches

    def build(
        self,
        output_path: str | Path = BOUNDARIES_PATH,
        manifest_path: str | Path = MANIFEST_PATH,
    ) -> dict:
        matches = self.reconcile()
        output_path = Path(output_path)
        manifest_path = Path(manifest_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        source_sha256 = hashlib.sha256(self.source_path.read_bytes()).hexdigest()
        generated_at = datetime.now(UTC).isoformat()
        features = []
        manifest_rows = []
        for match in matches:
            usable = match.geometry is not None
            point_inside = bool(
                usable
                and point_in_geometry(match.longitude, match.latitude, match.geometry)
            )
            if match.status == "exact" and point_inside:
                validation_grade = "A"
            elif match.status == "exact" or (match.status == "fuzzy" and point_inside):
                validation_grade = "B"
            elif usable:
                validation_grade = "C"
            else:
                validation_grade = "D"
            manifest_rows.append(
                {
                    "state": match.state,
                    "district": match.district,
                    "latitude": match.latitude,
                    "longitude": match.longitude,
                    "source_name": match.source_name,
                    "source_id": match.source_id,
                    "boundary_status": match.status,
                    "name_similarity": match.similarity,
                    "district_wide_usable": usable,
                    "representative_point_inside": point_inside,
                    "geographic_validation_grade": validation_grade,
                    "boundary_year": SOURCE["boundary_year"],
                }
            )
            if usable:
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "state": match.state,
                            "district": match.district,
                            "source_name": match.source_name,
                            "source_id": match.source_id,
                            "boundary_status": match.status,
                            "boundary_year": SOURCE["boundary_year"],
                        },
                        "geometry": match.geometry,
                    }
                )
        payload = {
            "type": "FeatureCollection",
            "metadata": {**SOURCE, "source_sha256": source_sha256, "generated_at": generated_at},
            "features": features,
        }
        output_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        manifest = pd.DataFrame(manifest_rows)
        manifest.to_csv(manifest_path, index=False)
        counts = manifest["boundary_status"].value_counts().to_dict()
        duplicate_source_ids = int(
            manifest.loc[manifest["district_wide_usable"], "source_id"].duplicated().sum()
        )
        summary = {
            "generated_at": generated_at,
            "districts": len(manifest),
            "usable_districts": int(manifest["district_wide_usable"].sum()),
            "coverage_percent": round(100 * manifest["district_wide_usable"].mean(), 2),
            "status_counts": {str(key): int(value) for key, value in counts.items()},
            "geographic_validation_grades": {
                str(key): int(value)
                for key, value in manifest["geographic_validation_grade"].value_counts().items()
            },
            "representative_points_inside": int(manifest["representative_point_inside"].sum()),
            "duplicate_source_ids": duplicate_source_ids,
            "source": SOURCE,
            "source_sha256": source_sha256,
        }
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    @staticmethod
    def aggregate_points(
        dataframe: pd.DataFrame,
        value_columns: Iterable[str],
        boundaries_path: str | Path = BOUNDARIES_PATH,
    ) -> pd.DataFrame:
        """Average grid cells inside each current, validated district polygon."""
        required = {"latitude", "longitude", *value_columns}
        missing = required - set(dataframe.columns)
        if missing:
            raise ValueError("Point dataset is missing: " + ", ".join(sorted(missing)))
        payload = json.loads(Path(boundaries_path).read_text(encoding="utf-8"))
        rows = []
        for feature in payload["features"]:
            geometry = feature["geometry"]
            minimum_x, minimum_y, maximum_x, maximum_y = geometry_bbox(geometry)
            candidates = dataframe.loc[
                dataframe["longitude"].between(minimum_x, maximum_x)
                & dataframe["latitude"].between(minimum_y, maximum_y)
            ]
            mask = [
                point_in_geometry(float(row.longitude), float(row.latitude), geometry)
                for row in candidates.itertuples(index=False)
            ]
            selected = candidates.loc[mask]
            row = dict(feature["properties"])
            row["grid_cell_count"] = len(selected)
            row["aggregation_status"] = "complete" if len(selected) else "no_grid_cells"
            for column in value_columns:
                row[column] = (
                    float(pd.to_numeric(selected[column], errors="coerce").mean())
                    if len(selected)
                    else math.nan
                )
            rows.append(row)
        return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("download", "build", "all", "status"), nargs="?", default="build"
    )
    arguments = parser.parse_args()
    registry = DistrictBoundaryRegistry()
    if arguments.command == "download":
        result = registry.download()
    elif arguments.command == "all":
        result = {"download": registry.download(), "build": registry.build()}
    elif arguments.command == "build":
        result = registry.build()
    else:
        if not SUMMARY_PATH.exists():
            raise SystemExit("Boundary summary does not exist. Run build first.")
        result = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
