"""Extract OSM district polygons from a GeoPackage without optional GIS libraries."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import struct
from datetime import UTC, datetime
from pathlib import Path

from scripts.sources.common.config import PROJECT_ROOT

OUTPUT_PATH = PROJECT_ROOT / "data/raw/geospatial/osm-ne-adm5-overrides.geojson"
TABLE = "gis_osm_adminareas_a_free"


class WKBReader:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.offset = 0

    def unpack(self, format_code: str, endian: str):
        size = struct.calcsize(format_code)
        value = struct.unpack_from(endian + format_code, self.payload, self.offset)
        self.offset += size
        return value[0] if len(value) == 1 else value

    def geometry(self) -> dict:
        endian = "<" if self.unpack("B", "<") == 1 else ">"
        geometry_type = int(self.unpack("I", endian))
        if geometry_type == 3:
            rings = []
            for _ in range(int(self.unpack("I", endian))):
                ring = [
                    [float(self.unpack("d", endian)), float(self.unpack("d", endian))]
                    for _ in range(int(self.unpack("I", endian)))
                ]
                rings.append(ring)
            return {"type": "Polygon", "coordinates": rings}
        if geometry_type == 6:
            polygons = []
            for _ in range(int(self.unpack("I", endian))):
                polygon = self.geometry()
                if polygon["type"] != "Polygon":
                    raise ValueError("GeoPackage multipolygon contains a non-polygon member.")
                polygons.append(polygon["coordinates"])
            return {"type": "MultiPolygon", "coordinates": polygons}
        raise ValueError(f"Unsupported WKB geometry type: {geometry_type}")


def decode_gpkg_geometry(payload: bytes) -> dict:
    if payload[:2] != b"GP":
        raise ValueError("Invalid GeoPackage geometry header.")
    flags = payload[3]
    envelope_code = (flags >> 1) & 0b111
    envelope_doubles = {0: 0, 1: 4, 2: 6, 3: 6, 4: 8}.get(envelope_code)
    if envelope_doubles is None:
        raise ValueError(f"Unsupported GeoPackage envelope code: {envelope_code}")
    header_size = 8 + envelope_doubles * 8
    return WKBReader(payload[header_size:]).geometry()


def extract(source: Path, destination: Path = OUTPUT_PATH) -> dict:
    if not source.exists():
        raise FileNotFoundError(source)
    connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            f"SELECT osm_id, name, geom FROM {TABLE} "
            "WHERE fclass = 'admin_level5' AND geom IS NOT NULL ORDER BY name"
        ).fetchall()
    finally:
        connection.close()
    features = [
        {
            "type": "Feature",
            "properties": {
                "shapeName": str(name),
                "shapeID": f"osm-{osm_id}",
                "provider": "Geofabrik OpenStreetMap extract",
                "admin_level": 5,
            },
            "geometry": decode_gpkg_geometry(geometry),
        }
        for osm_id, name, geometry in rows
    ]
    generated_at = datetime.now(UTC).isoformat()
    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "provider": "Geofabrik OpenStreetMap extract",
            "license": "ODbL 1.0",
            "source_file": source.name,
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "admin_level": 5,
            "generated_at": generated_at,
        },
        "features": features,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    temporary.replace(destination)
    return {
        "generated_at": generated_at,
        "features": len(features),
        "output": str(destination),
        "source_sha256": payload["metadata"]["source_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    arguments = parser.parse_args()
    print(json.dumps(extract(arguments.source, arguments.output), indent=2))


if __name__ == "__main__":
    main()
