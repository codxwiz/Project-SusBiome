import unittest

import numpy as np
import pandas as pd

from scripts.ml.evaluation import (
    alert_budget_threshold,
    alert_burden_metrics,
    event_ranking_metrics,
)


class EventEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.probabilities = np.array([0.9, 0.8, 0.2, 0.1, 0.7, 0.6, 0.4, 0.3])
        self.target = pd.Series([1, 0, 0, 0, 0, 1, 0, 0])
        self.groups = pd.Series(["event-a", "", "", "", "", "event-b", "", ""])
        self.dates = pd.Series(["2024-01-01"] * 4 + ["2024-01-02"] * 4)

    def test_event_ranking_uses_best_daily_rank_per_event(self):
        metrics = event_ranking_metrics(
            self.probabilities, self.target, self.groups, self.dates
        )

        self.assertEqual(metrics["independent_events"], 2)
        self.assertEqual(metrics["top_0.05_fraction"]["detected_events"], 0)
        self.assertEqual(metrics["median_best_daily_rank_fraction"], 0.375)

    def test_alert_budget_threshold_and_burden(self):
        threshold = alert_budget_threshold(self.probabilities, 0.25)
        metrics = alert_burden_metrics(
            self.probabilities,
            self.target,
            self.groups,
            self.dates,
            threshold=threshold,
        )

        self.assertEqual(threshold, 0.8)
        self.assertEqual(metrics["alerted_rows"], 2)
        self.assertEqual(metrics["detected_events"], 1)

    def test_invalid_alert_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            alert_budget_threshold(self.probabilities, 1.0)


if __name__ == "__main__":
    unittest.main()
