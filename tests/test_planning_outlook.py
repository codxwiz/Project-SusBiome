from __future__ import annotations

import unittest

import pandas as pd

from scripts.serving.planning_outlook import OUTLOOK_HORIZONS, build_planning_outlook


class PlanningOutlookTests(unittest.TestCase):
    def setUp(self):
        self.assessment = pd.DataFrame(
            {
                "state": ["Assam"],
                "district": ["Dibrugarh"],
                "horizon_days": [14],
                "valid_from": [pd.Timestamp("2026-07-01")],
                "latitude": [27.48],
                "longitude": [94.91],
                "flood_weather_risk_score": [90.0],
                "flood_susceptibility": [0.30],
                "drought_weather_risk_score": [10.0],
                "drought_susceptibility": [0.60],
                "cyclone_weather_risk_score": [50.0],
                "cyclone_susceptibility": [0.20],
            }
        )

    def test_builds_requested_horizons_and_only_three_hazards(self):
        result = build_planning_outlook(self.assessment)
        self.assertEqual(result["outlook_horizon_days"].tolist(), list(OUTLOOK_HORIZONS))
        self.assertTrue(
            {
                "flood_outlook_score",
                "drought_outlook_score",
                "cyclone_outlook_score",
            }.issubset(result.columns)
        )

    def test_longer_horizons_move_toward_historical_susceptibility(self):
        result = build_planning_outlook(self.assessment)
        self.assertGreater(
            result.iloc[0]["flood_outlook_score"], result.iloc[-1]["flood_outlook_score"]
        )
        self.assertLess(
            result.iloc[0]["drought_outlook_score"], result.iloc[-1]["drought_outlook_score"]
        )
        self.assertFalse(result["outlook_is_probability"].any())


if __name__ == "__main__":
    unittest.main()
