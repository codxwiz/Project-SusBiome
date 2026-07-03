from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from pathlib import Path

import pandas as pd

from scripts.forecast.open_meteo import OpenMeteoForecastCollector
from scripts.geospatial.districts import DistrictBoundaryRegistry, point_in_geometry
from scripts.serving.district_assessment import (
    AssessmentUnavailableError,
    district_report,
    load_current_assessment,
)
from scripts.serving.location_assessment import location_report


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
    def test_stale_serving_data_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assessment.parquet"
            pd.DataFrame(
                {"collected_at": [datetime.now(UTC) - timedelta(hours=40)], "value": [1]}
            ).to_parquet(path, index=False)
            with self.assertRaisesRegex(AssessmentUnavailableError, "stale"):
                load_current_assessment(path, max_age_hours=36)

    def test_report_keeps_weather_score_separate_from_probability(self):
        row = pd.Series(
            {
                "state": "Assam",
                "district": "Dibrugarh",
                "horizon_days": 7,
                "valid_from": pd.Timestamp("2026-01-01"),
                "valid_to": pd.Timestamp("2026-01-07"),
                "assessment_available": True,
                "vulnerability_available": False,
                "assessment_scope": "district_weather_hazard_outlook",
                "assessment_method": "weather_pattern_index_v1",
                "confidence_grade": "A",
                "confidence_reason": "Weather assessment available.",
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
                        ("weather_risk_score", 62.5),
                        ("probability", float("nan")),
                        ("susceptibility", 0.5),
                        ("land_risk_index", 0.625),
                        ("risk_level", "HIGH"),
                        ("risk_drivers", json.dumps(["Test driver"])),
                    )
                },
            }
        )
        report = district_report(row)
        self.assertEqual(report["hazards"]["flood"]["forecast_signal"], 0.7)
        self.assertIsNone(report["hazards"]["flood"]["probability"])
        self.assertEqual(report["hazards"]["flood"]["weather_risk_score"], 62.5)
        self.assertEqual(report["hazards"]["flood"]["risk_level"], "HIGH")

    def test_location_report_keeps_probability_separate(self):
        with (
            patch(
                "scripts.serving.location_assessment.locate_district",
                return_value={
                    "state": "Assam",
                    "district": "Dibrugarh",
                    "match_method": "district_polygon",
                    "distance_km": 0.0,
                },
            ),
            patch(
                "scripts.serving.location_assessment._srtm_context",
                return_value={"elevation_m": 100.0, "slope_degrees": 2.0},
            ),
            patch(
                "scripts.serving.location_assessment._worldcover_context",
                return_value={"class_code": 40, "class_name": "cropland"},
            ),
        ):
            report = location_report(27.48, 94.91, 7)
        self.assertTrue(report["context_available"])
        self.assertIsNone(report["hazards"]["flood"]["probability"])
        self.assertEqual(report["assessment_method"], "location_weather_land_index_v1")


if __name__ == "__main__":
    unittest.main()
