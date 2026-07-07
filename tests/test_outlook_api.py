from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from scripts.api.app import app


class OutlookApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_outlook_bundle_serves_frontend_contract(self):
        response = self.client.get("/api/outlook")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["districts"], 133)
        self.assertEqual(payload["meta"]["horizons"], [15, 30, 60, 90])
        self.assertEqual(payload["meta"]["hazards"], ["flood", "drought", "cyclone"])
        self.assertFalse(payload["meta"]["outlookIsProbability"])
        self.assertEqual(len(payload["outlook"]), 532)

    def test_district_filter_and_horizon_selection(self):
        response = self.client.get("/api/outlook/Assam/Dibrugarh?horizon=30")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["state"], "Assam")
        self.assertEqual(payload["district"], "Dibrugarh")
        self.assertEqual(len(payload["outlook"]), 1)
        self.assertEqual(payload["outlook"][0]["horizon"], 30)
        self.assertIn("flood", payload["outlook"][0]["hazards"])

    def test_state_boundaries_can_be_filtered(self):
        response = self.client.get("/api/outlook/boundaries?state=Assam")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["type"], "FeatureCollection")
        self.assertTrue(payload["features"])
        self.assertTrue(
            all(feature["properties"]["state"] == "Assam" for feature in payload["features"])
        )


if __name__ == "__main__":
    unittest.main()
