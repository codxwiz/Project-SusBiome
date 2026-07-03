from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from ground_truth.build import build
from scripts.quality.audit import audit_owner_review
from scripts.quality.production_review import _spread


class ProductionReviewTests(unittest.TestCase):
    def test_spread_selects_requested_rows(self):
        selected = _spread(pd.DataFrame({"value": range(100)}), 15)
        self.assertEqual(len(selected), 15)
        self.assertEqual(selected.iloc[0]["value"], 0)
        self.assertEqual(selected.iloc[-1]["value"], 99)

    def test_pending_review_blocks_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "data/quality/production_event_review.csv"
            path.parent.mkdir(parents=True)
            pd.DataFrame(
                {
                    "hazard_type": ["FLOOD"],
                    "review_status": ["PENDING"],
                    "event_occurred_in_district": [""],
                    "date_correct": [""],
                }
            ).to_csv(path, index=False)
            with patch("scripts.quality.audit.PROJECT_ROOT", root):
                findings = audit_owner_review()
        self.assertEqual(findings[0].check, "owner_review.pending")

    def test_rejected_decision_removes_event_from_canonical_build(self):
        event = pd.DataFrame(
            {
                "event_date": ["2024-07-01"],
                "hazard_type": ["FLOOD"],
                "state": ["Assam"],
                "district": ["Dibrugarh"],
                "source_event_id": ["event-1"],
                "latitude": [27.48],
                "longitude": [94.91],
                "verified": [True],
                "confidence": [95],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            decision = Path(directory) / "review.csv"
            pd.DataFrame(
                {
                    "event_date": ["2024-07-01"],
                    "hazard_type": ["FLOOD"],
                    "state": ["Assam"],
                    "district": ["Dibrugarh"],
                    "source_event_id": ["event-1"],
                    "review_status": ["REJECTED"],
                    "event_occurred_in_district": ["NO"],
                    "date_correct": ["YES"],
                }
            ).to_csv(decision, index=False)
            with patch("ground_truth.build.PRODUCTION_REVIEW", decision):
                accepted, review = build(event)
        self.assertTrue(accepted.empty)
        self.assertEqual(len(review), 1)


if __name__ == "__main__":
    unittest.main()
