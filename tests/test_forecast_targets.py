from __future__ import annotations

import unittest

import pandas as pd

from scripts.labels.forecast_targets import add_future_targets, prepare_events


class ForecastTargetTests(unittest.TestCase):
    def test_targets_only_dates_before_event(self):
        event = pd.DataFrame(
            {
                "event_date": [pd.Timestamp("2024-01-10", tz="UTC")],
                "hazard_type": ["FLOOD"],
                "latitude": [26.01],
                "longitude": [92.01],
                "verified": [True],
                "source": ["test"],
                "source_event_id": ["flood-1"],
                "event_id": ["event-1"],
            }
        )
        features = pd.DataFrame(
            {
                "valid_time": pd.date_range("2024-01-01", "2024-01-12", tz="UTC"),
                "latitude": 26.0,
                "longitude": 92.0,
            }
        )
        result = add_future_targets(features, prepare_events(event))
        positive_dates = result.loc[result["flood_risk_3d"].eq(1), "valid_time"].tolist()
        self.assertEqual(
            positive_dates,
            list(pd.date_range("2024-01-07", "2024-01-09", tz="UTC")),
        )
        self.assertEqual(int(result.loc[result["valid_time"].eq(event.event_date[0]), "flood_risk_14d"].iloc[0]), 0)

    def test_targets_preserve_independent_event_group(self):
        event = pd.DataFrame(
            {
                "event_date": [pd.Timestamp("2024-01-10", tz="UTC")],
                "hazard_type": ["CYCLONE"],
                "latitude": [26.0],
                "longitude": [92.0],
                "verified": [True],
                "source": ["ibtracs"],
                "source_event_id": ["storm-1"],
                "event_id": ["row-1"],
            }
        )
        features = pd.DataFrame(
            {
                "valid_time": [pd.Timestamp("2024-01-09", tz="UTC")],
                "latitude": [26.0],
                "longitude": [92.0],
            }
        )
        result = add_future_targets(features, prepare_events(event))
        self.assertEqual(result.loc[0, "cyclone_event_group_3d"], "storm-1")
        self.assertEqual(int(result.loc[0, "cyclone_lead_days_3d"]), 1)


if __name__ == "__main__":
    unittest.main()
