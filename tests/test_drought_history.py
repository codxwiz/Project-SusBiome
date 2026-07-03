from __future__ import annotations

import unittest

import pandas as pd

from scripts.events.drought_history import episodes_from_days


class DroughtHistoryTests(unittest.TestCase):
    def test_long_contiguous_pattern_becomes_episode(self):
        dates = pd.date_range("2024-01-01", periods=14, tz="UTC")
        frame = pd.DataFrame(
            {
                "state": "Assam",
                "district": "Dibrugarh",
                "valid_time": dates,
                "drought_pattern_day": True,
                "precipitation_90d_sum": 20.0,
                "soil_moisture_30d_mean": 0.1,
                "water_balance_30d": -30.0,
                "consecutive_dry_days": range(7, 21),
            }
        )
        result = episodes_from_days(frame)

        self.assertEqual(len(result), 1)
        self.assertEqual(int(result.loc[0, "duration_days"]), 14)
        self.assertFalse(bool(result.loc[0, "verified_disaster_event"]))

    def test_short_pattern_is_not_an_episode(self):
        frame = pd.DataFrame(
            {
                "state": ["Assam"] * 5,
                "district": ["Dibrugarh"] * 5,
                "valid_time": pd.date_range("2024-01-01", periods=5, tz="UTC"),
                "drought_pattern_day": True,
                "precipitation_90d_sum": 20.0,
                "soil_moisture_30d_mean": 0.1,
                "water_balance_30d": -30.0,
                "consecutive_dry_days": range(7, 12),
            }
        )
        self.assertTrue(episodes_from_days(frame).empty)


if __name__ == "__main__":
    unittest.main()
