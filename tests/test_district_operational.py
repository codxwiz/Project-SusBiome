from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.forecast.open_meteo import OpenMeteoForecastCollector
from scripts.geospatial.districts import DistrictBoundaryRegistry, point_in_geometry
from scripts.serving.district_assessment import district_report


class DistrictGeometryTests(unittest.TestCase):
    def setUp(self):
        self.geometry = {
            "type": "Polygon",
            "coordinates": [
                [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]],
                [[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]],
            ],
        }

    def test_point_in_geometry_respects_holes_and_boundaries(self):
        self.assertTrue(point_in_geometry(0.5, 0.5, self.geometry))
        self.assertFalse(point_in_geometry(2.0, 2.0, self.geometry))
        self.assertTrue(point_in_geometry(0.0, 2.0, self.geometry))
        self.assertFalse(point_in_geometry(5.0, 2.0, self.geometry))

    def test_polygon_aggregation_uses_only_contained_grid_cells(self):
        dataframe = pd.DataFrame(
            {
                "latitude": [0.5, 2.0, 5.0],
                "longitude": [0.5, 2.0, 5.0],
                "rain": [10.0, 100.0, 1000.0],
            }
        )
        payload = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"state": "State", "district": "District"},
                    "geometry": self.geometry,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "boundaries.geojson"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = DistrictBoundaryRegistry.aggregate_points(dataframe, ["rain"], path)
        self.assertEqual(result.loc[0, "grid_cell_count"], 1)
        self.assertEqual(result.loc[0, "rain"], 10.0)


class ForecastContractTests(unittest.TestCase):
    def test_horizon_contract_has_three_complete_windows(self):
        dates = pd.date_range("2026-01-01", periods=14, freq="D")
        daily = pd.DataFrame(
            {
                "state": "Assam",
                "district": "Dibrugarh",
                "latitude": 27.48,
                "longitude": 94.91,
                "valid_date": dates,
                "lead_day": range(1, 15),
                "precipitation_sum": 10.0,
                "precipitation_probability_max": 80,
                "temperature_2m_max": 30.0,
                "temperature_2m_min": 20.0,
                "wind_speed_10m_max": 15.0,
                "wind_gusts_10m_max": 25.0,
                "et0_fao_evapotranspiration": 3.0,
                "collected_at": "2026-01-01T00:00:00+00:00",
            }
        )
        result = OpenMeteoForecastCollector.build_horizons(daily)
        self.assertEqual(result["horizon_days"].tolist(), [3, 7, 14])
        self.assertEqual(result["precipitation_sum_mm"].tolist(), [30.0, 70.0, 140.0])


class AssessmentReportTests(unittest.TestCase):
    def test_report_keeps_signal_separate_from_unavailable_probability(self):
        row = pd.Series(
            {
                "state": "Assam",
                "district": "Dibrugarh",
                "horizon_days": 7,
                "valid_from": pd.Timestamp("2026-01-01"),
                "valid_to": pd.Timestamp("2026-01-07"),
                "assessment_available": False,
                "vulnerability_available": False,
                "assessment_scope": "land_hazard_only",
                "confidence_grade": "D",
                "confidence_reason": "Model unavailable.",
                "static_factor_coverage": 0.4,
                "boundary_status": "exact",
                "precipitation_sum_mm": 120.0,
                "precipitation_probability_max": 90,
                "wind_gust_max_kmh": 40.0,
                "temperature_max_c": 31.0,
                "temperature_min_c": 20.0,
                "provider": "Open-Meteo",
                "spatial_support": "representative_point",
                "mitigation_actions": json.dumps(["Monitor conditions."]),
                **{
                    f"{hazard}_{name}": value
                    for hazard in ("flood", "cyclone", "drought")
                    for name, value in (
                        ("forecast_signal", 0.7),
                        ("probability", float("nan")),
                        ("susceptibility", 0.5),
                        ("land_risk_index", float("nan")),
                        ("risk_level", "UNAVAILABLE"),
                    )
                },
            }
        )
        report = district_report(row)
        self.assertEqual(report["hazards"]["flood"]["forecast_signal"], 0.7)
        self.assertIsNone(report["hazards"]["flood"]["probability"])
        self.assertEqual(report["hazards"]["flood"]["risk_level"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
