"""Collect reproducible SRTM terrain and ESA WorldCover land context."""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests

from scripts.geospatial.districts import (
    BOUNDARIES_PATH,
    MANIFEST_PATH,
    geometry_bbox,
    point_in_geometry,
)
from scripts.sources.common.config import EARTHDATA_TOKEN, PROJECT_ROOT

SRTM_ROOT = PROJECT_ROOT / "data/bronze/terrain/srtmgl1_v003"
WORLDCOVER_ROOT = PROJECT_ROOT / "data/bronze/land_cover/worldcover_2021_v200"
TERRAIN_PATH = PROJECT_ROOT / "data/silver/susceptibility/terrain.parquet"
LAND_COVER_PATH = PROJECT_ROOT / "data/silver/susceptibility/land_cover.parquet"
CONTEXT_MANIFEST_PATH = PROJECT_ROOT / "data/silver/susceptibility/land_context_manifest.json"

SRTM_URL = (
    "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/"
    "SRTMGL1.003/{tile}.SRTMGL1.hgt/{tile}.SRTMGL1.hgt.zip"
)
WORLDCOVER_URL = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
    "ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
)

WORLD_COVER_CLASSES = {
    10: "tree_cover",
    20: "shrubland",
    30: "grassland",
    40: "cropland",
    50: "built_up",
    60: "bare_sparse_vegetation",
    70: "snow_ice",
    80: "permanent_water",
    90: "herbaceous_wetland",
    95: "mangroves",
    100: "moss_lichen",
}

FLOOD_CLASS_SCORE = {
    10: 0.30, 20: 0.40, 30: 0.45, 40: 0.60, 50: 0.75, 60: 0.55,
    70: 0.20, 80: 0.90, 90: 0.85, 95: 0.80, 100: 0.35,
}
CYCLONE_CLASS_SCORE = {
    10: 0.35, 20: 0.35, 30: 0.45, 40: 0.55, 50: 0.70, 60: 0.45,
    70: 0.20, 80: 0.35, 90: 0.45, 95: 0.50, 100: 0.30,
}
DROUGHT_CLASS_SCORE = {
    10: 0.25, 20: 0.55, 30: 0.65, 40: 0.75, 50: 0.45, 60: 0.85,
    70: 0.20, 80: 0.10, 90: 0.15, 95: 0.20, 100: 0.40,
}


def _atomic_parquet(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    dataframe.to_parquet(temporary, index=False, compression="snappy")
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def polygon_samples(geometry: dict | None, count: int = 5) -> list[tuple[float, float]]:
    """Return deterministic interior latitude/longitude samples."""
    if not geometry:
        return []
    minimum_x, minimum_y, maximum_x, maximum_y = geometry_bbox(geometry)
    samples = []
    for latitude in np.linspace(minimum_y, maximum_y, count + 2)[1:-1]:
        for longitude in np.linspace(minimum_x, maximum_x, count + 2)[1:-1]:
            if point_in_geometry(float(longitude), float(latitude), geometry):
                samples.append((float(latitude), float(longitude)))
    return samples


def _district_samples(count: int = 5) -> list[dict]:
    manifest = pd.read_csv(MANIFEST_PATH)
    boundaries = json.loads(BOUNDARIES_PATH.read_text(encoding="utf-8"))
    geometries = {
        (feature["properties"]["state"], feature["properties"]["district"]): feature["geometry"]
        for feature in boundaries["features"]
    }
    records = []
    for row in manifest.itertuples(index=False):
        points = polygon_samples(geometries.get((row.state, row.district)), count=count)
        support = "district_polygon_stratified_samples"
        if not points:
            points = [(float(row.latitude), float(row.longitude))]
            support = "representative_point"
        records.append(
            {"state": row.state, "district": row.district, "support": support, "points": points}
        )
    return records


def srtm_tile(latitude: float, longitude: float) -> str:
    south = math.floor(latitude)
    west = math.floor(longitude)
    return f"{'N' if south >= 0 else 'S'}{abs(south):02d}{'E' if west >= 0 else 'W'}{abs(west):03d}"


def worldcover_tile(latitude: float, longitude: float) -> str:
    south = math.floor(latitude / 3) * 3
    west = math.floor(longitude / 3) * 3
    return f"{'N' if south >= 0 else 'S'}{abs(south):02d}{'E' if west >= 0 else 'W'}{abs(west):03d}"


class _Downloader:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def get(self, url: str, destination: Path, *, minimum_bytes: int) -> Path:
        if destination.exists() and destination.stat().st_size >= minimum_bytes:
            return destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".download")
        error: Exception | None = None
        try:
            for attempt in range(5):
                try:
                    with self.session.get(url, stream=True, timeout=(30, 300)) as response:
                        response.raise_for_status()
                        with temporary.open("wb") as output:
                            for chunk in response.iter_content(1024 * 1024):
                                if chunk:
                                    output.write(chunk)
                    if temporary.stat().st_size < minimum_bytes:
                        raise IOError(f"Downloaded artifact is too small: {url}")
                    os.replace(temporary, destination)
                    return destination
                except (requests.RequestException, OSError) as caught:
                    error = caught
                    if attempt < 4:
                        time.sleep(min(2**attempt, 20))
        finally:
            temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Download failed after retries: {url}: {error}")


class SRTMTerrainCollector:
    """Collect 30 m terrain summaries from authenticated NASA SRTMGL1 tiles."""

    def __init__(self, session: requests.Session | None = None) -> None:
        if not EARTHDATA_TOKEN:
            raise RuntimeError("EARTHDATA_TOKEN is required for NASA SRTM collection.")
        self.session = session or requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {EARTHDATA_TOKEN}"})
        self.downloader = _Downloader(self.session)

    def _download(self, tile: str) -> Path:
        path = SRTM_ROOT / f"{tile}.SRTMGL1.hgt.zip"
        return self.downloader.get(SRTM_URL.format(tile=tile), path, minimum_bytes=100_000)

    @staticmethod
    def _read(path: Path) -> np.ndarray:
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".hgt")]
            if len(members) != 1:
                raise ValueError(f"Expected one HGT member in {path}")
            payload = archive.read(members[0])
        side = int(math.sqrt(len(payload) / 2))
        if side * side * 2 != len(payload):
            raise ValueError(f"Invalid SRTM grid dimensions in {path}")
        return np.frombuffer(payload, dtype=">i2").reshape(side, side)

    @staticmethod
    def _sample(array: np.ndarray, latitude: float, longitude: float) -> tuple[float, float]:
        side = array.shape[0]
        south = math.floor(latitude)
        west = math.floor(longitude)
        row = int(round((south + 1 - latitude) * (side - 1)))
        column = int(round((longitude - west) * (side - 1)))
        row = min(max(row, 1), side - 2)
        column = min(max(column, 1), side - 2)
        neighborhood = array[row - 1 : row + 2, column - 1 : column + 2].astype(float)
        elevation = float(neighborhood[1, 1])
        if (neighborhood <= -32_000).any():
            return math.nan, math.nan
        dx = 111_320 * math.cos(math.radians(latitude)) / (side - 1)
        dy = 110_574 / (side - 1)
        dzdx = (neighborhood[1, 2] - neighborhood[1, 0]) / (2 * dx)
        dzdy = (neighborhood[0, 1] - neighborhood[2, 1]) / (2 * dy)
        slope = math.degrees(math.atan(math.sqrt(dzdx**2 + dzdy**2)))
        return elevation, slope

    def collect(self, output_path: str | Path = TERRAIN_PATH) -> dict:
        districts = _district_samples(count=5)
        needed = sorted(
            {srtm_tile(latitude, longitude) for item in districts for latitude, longitude in item["points"]}
        )
        paths = {tile: self._download(tile) for tile in needed}
        arrays = {tile: self._read(path) for tile, path in paths.items()}
        rows = []
        collected_at = datetime.now(UTC).isoformat()
        for item in districts:
            samples = [
                self._sample(arrays[srtm_tile(latitude, longitude)], latitude, longitude)
                for latitude, longitude in item["points"]
            ]
            elevations = np.asarray([value[0] for value in samples], dtype=float)
            slopes = np.asarray([value[1] for value in samples], dtype=float)
            valid = np.isfinite(elevations) & np.isfinite(slopes)
            if not valid.any():
                raise ValueError(f"No valid SRTM samples for {item['state']} / {item['district']}")
            elevations = elevations[valid]
            slopes = slopes[valid]
            rows.append(
                {
                    "state": item["state"],
                    "district": item["district"],
                    "elevation_mean_m": round(float(elevations.mean()), 2),
                    "elevation_min_m": round(float(elevations.min()), 2),
                    "elevation_max_m": round(float(elevations.max()), 2),
                    "terrain_relief_m": round(float(elevations.max() - elevations.min()), 2),
                    "slope_mean_degrees": round(float(slopes.mean()), 3),
                    "slope_p95_degrees": round(float(np.quantile(slopes, 0.95)), 3),
                    "terrain_sample_count": int(valid.sum()),
                    "terrain_spatial_support": item["support"],
                    "terrain_source": "NASA SRTMGL1 v003 1 arc-second (approximately 30 m)",
                    "terrain_collected_at": collected_at,
                }
            )
        terrain = pd.DataFrame(rows)
        _atomic_parquet(terrain, Path(output_path))
        return {
            "collected_at": collected_at,
            "districts": len(terrain),
            "tiles": len(paths),
            "sample_points": int(terrain["terrain_sample_count"].sum()),
            "source": "NASA SRTMGL1 v003",
            "tile_checksums": {tile: _sha256(path) for tile, path in paths.items()},
            "output": str(Path(output_path)),
        }


class WorldCoverCollector:
    """Collect sampled district land-cover fractions from ESA WorldCover 2021."""

    def __init__(self, session: requests.Session | None = None) -> None:
        self.downloader = _Downloader(session)

    def _download(self, tile: str) -> Path:
        path = WORLDCOVER_ROOT / f"ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
        return self.downloader.get(WORLDCOVER_URL.format(tile=tile), path, minimum_bytes=1_000_000)

    @staticmethod
    def _scores(values: np.ndarray, mapping: dict[int, float]) -> float:
        scores = [mapping[int(value)] for value in values if int(value) in mapping]
        return float(np.mean(scores)) if scores else math.nan

    def collect(self, output_path: str | Path = LAND_COVER_PATH) -> dict:
        districts = _district_samples(count=7)
        needed = sorted(
            {
                worldcover_tile(latitude, longitude)
                for item in districts
                for latitude, longitude in item["points"]
            }
        )
        paths = {tile: self._download(tile) for tile in needed}
        datasets = {tile: rasterio.open(path) for tile, path in paths.items()}
        rows = []
        collected_at = datetime.now(UTC).isoformat()
        try:
            for item in districts:
                by_tile: dict[str, list[tuple[float, float]]] = {}
                for latitude, longitude in item["points"]:
                    by_tile.setdefault(worldcover_tile(latitude, longitude), []).append(
                        (longitude, latitude)
                    )
                values = []
                for tile, coordinates in by_tile.items():
                    values.extend(int(sample[0]) for sample in datasets[tile].sample(coordinates))
                data = np.asarray([value for value in values if value in WORLD_COVER_CLASSES])
                if data.size == 0:
                    raise ValueError(
                        f"No valid WorldCover samples for {item['state']} / {item['district']}"
                    )
                counts = pd.Series(data).value_counts(normalize=True)
                row = {
                    "state": item["state"],
                    "district": item["district"],
                    "land_cover_sample_count": int(data.size),
                    "land_cover_spatial_support": item["support"],
                    "land_cover_source": "ESA WorldCover 2021 v200 10 m",
                    "land_cover_collected_at": collected_at,
                    "flood_land_cover_score": self._scores(data, FLOOD_CLASS_SCORE),
                    "cyclone_land_cover_score": self._scores(data, CYCLONE_CLASS_SCORE),
                    "drought_land_cover_score": self._scores(data, DROUGHT_CLASS_SCORE),
                    "dominant_land_cover_class": WORLD_COVER_CLASSES[int(counts.idxmax())],
                }
                for code, name in WORLD_COVER_CLASSES.items():
                    row[f"{name}_fraction"] = float(counts.get(code, 0.0))
                rows.append(row)
        finally:
            for dataset in datasets.values():
                dataset.close()
        land_cover = pd.DataFrame(rows)
        _atomic_parquet(land_cover, Path(output_path))
        return {
            "collected_at": collected_at,
            "districts": len(land_cover),
            "tiles": len(paths),
            "sample_points": int(land_cover["land_cover_sample_count"].sum()),
            "source": "ESA WorldCover 2021 v200",
            "tile_checksums": {tile: _sha256(path) for tile, path in paths.items()},
            "output": str(Path(output_path)),
        }


def collect_all() -> dict:
    result = {
        "terrain": SRTMTerrainCollector().collect(),
        "land_cover": WorldCoverCollector().collect(),
    }
    CONTEXT_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTEXT_MANIFEST_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
