from __future__ import annotations

import struct
import unittest

from scripts.geospatial.osm_gpkg import decode_gpkg_geometry


def polygon_gpkg() -> bytes:
    ring = [(91.0, 26.0), (92.0, 26.0), (92.0, 27.0), (91.0, 26.0)]
    wkb = bytearray(struct.pack("<BI", 1, 3))
    wkb.extend(struct.pack("<I", 1))
    wkb.extend(struct.pack("<I", len(ring)))
    for point in ring:
        wkb.extend(struct.pack("<dd", *point))
    return b"GP" + bytes([0, 1]) + struct.pack("<i", 4326) + bytes(wkb)


class GeoPackageGeometryTests(unittest.TestCase):
    def test_decodes_polygon_geometry(self):
        geometry = decode_gpkg_geometry(polygon_gpkg())

        self.assertEqual(geometry["type"], "Polygon")
        self.assertEqual(geometry["coordinates"][0][1], [92.0, 26.0])

    def test_rejects_invalid_header(self):
        with self.assertRaisesRegex(ValueError, "header"):
            decode_gpkg_geometry(b"not-a-geopackage-geometry")


if __name__ == "__main__":
    unittest.main()
