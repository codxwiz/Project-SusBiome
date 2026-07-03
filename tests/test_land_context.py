from __future__ import annotations

import unittest

import numpy as np

from scripts.serving.location_assessment import _point_factor, locate_district
from scripts.susceptibility.land_context import (
    SRTMTerrainCollector,
    srtm_tile,
    worldcover_tile,
)


class LandContextTests(unittest.TestCase):
    def test_tile_names_follow_source_grids(self):
        self.assertEqual(srtm_tile(27.48, 94.91), "N27E094")
        self.assertEqual(worldcover_tile(27.48, 94.91), "N27E093")

    def test_srtm_sample_returns_elevation_and_slope(self):
        grid = np.arange(25, dtype=">i2").reshape(5, 5)
        elevation, slope = SRTMTerrainCollector._sample(grid, 27.5, 94.5)
        self.assertEqual(elevation, 12.0)
        self.assertGreater(slope, 0.0)

    def test_known_point_matches_dibrugarh(self):
        match = locate_district(27.48, 94.91)
        self.assertEqual(match["state"], "Assam")
        self.assertEqual(match["district"], "Dibrugarh")

    def test_flood_point_factor_combines_terrain_and_land_cover(self):
        factor = _point_factor(
            "flood",
            {"elevation_m": 100.0, "slope_degrees": 2.0},
            {"class_code": 50},
        )
        self.assertIsNotNone(factor)
        self.assertGreater(factor, 0.7)

    def test_district_fallback_has_no_point_factor(self):
        self.assertIsNone(_point_factor("drought", None, None))


if __name__ == "__main__":
    unittest.main()
