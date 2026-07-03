from __future__ import annotations

import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI
from fastapi import Response
from fastapi.testclient import TestClient
import numpy as np
import pandas as pd

from scripts.api.models import DEFAULT_FEATURE_FILE, resolve_data_path
from scripts.fusion.align import DataAligner
from scripts.features.engineering import FeatureEngineering
from scripts.ml.dataset import MLDataset
from scripts.ml.models import FEATURE_COLUMNS
from scripts.ml.evaluation import release_quality
from scripts.prediction.inference import PredictionInference
from scripts.prediction.loader import PredictionLoader
from scripts.risk.combined import CombinedRisk
from scripts.risk.models import validate_prediction_values
from scripts.events.classify_gdelt_candidates import classify_event, parse_event_date
from scripts.features.hazards import build_features
from scripts.fusion.historical import fuse_frames
from scripts.ingestion.historical_weather import era5_request
from scripts.labels.verified import align_events, prepare_events
from scripts.api.dependencies import require_api_key
from scripts.api.dependencies import dependency_errors, dependency_status
from scripts.monitoring.drift import drift_report
from ground_truth.build import normalize
from ground_truth.collectors.collect_gdacs import _geometry_contains
from scripts.dashboard.loader import DashboardLoader
from scripts.api.middleware import configure_middleware
from scripts.ml.registry import ModelRegistry
from scripts.risk.orchestrator import RiskOrchestrator
from scripts.production_pipeline import collection_complete
from scripts.api.routers.health import readiness


class SingleClassModel:
    classes_ = np.array([0])

    def predict_proba(self, values):
        return np.ones((len(values), 1))


class ContractModel:
    classes_ = np.array([0, 1])
    feature_names_in_ = np.array(FEATURE_COLUMNS)

    def predict(self, values):
        return np.zeros(len(values))

    def predict_proba(self, values):
        return np.zeros((len(values), 2))


class ThresholdModel:
    classes_ = np.array([0, 1])
    susbiome_threshold_ = 0.7

    def predict_proba(self, values):
        return np.array([[0.4, 0.6], [0.2, 0.8]])


class OptionalDroughtLoader:
    def load_all(self):
        return {"flood": ContractModel(), "cyclone": ContractModel(), "drought": None}


class ProductionGuardTests(unittest.TestCase):
    def test_release_quality_rejects_high_accuracy_low_recall_models(self):
        metrics = {
            "flood": {
                "accuracy": 0.99, "balanced_accuracy": 0.64, "precision": 0.03,
                "recall": 0.29, "pr_auc": 0.01, "true_positive": 6,
            },
            "cyclone": {
                "accuracy": 0.99, "balanced_accuracy": 0.80, "precision": 0.40,
                "recall": 0.70, "pr_auc": 0.30, "true_positive": 20,
            },
        }
        quality = release_quality(metrics)
        self.assertFalse(quality["passed"])
        self.assertTrue(any("flood.recall" in item for item in quality["findings"]))

    def test_optional_drought_does_not_block_production_risk(self):
        row = {
            "valid_time": pd.Timestamp("2026-01-01", tz="UTC"),
            "latitude": 26.0,
            "longitude": 92.0,
            **{column: 1.0 for column in FEATURE_COLUMNS},
        }
        predictions = PredictionInference(OptionalDroughtLoader()).predict(pd.DataFrame([row]))
        self.assertFalse(bool(predictions.iloc[0]["drought_available"]))
        self.assertTrue(pd.isna(predictions.iloc[0]["drought_probability"]))
        risk, _ = RiskOrchestrator().build(predictions)
        self.assertEqual(risk.iloc[0]["drought_risk_level"], "UNAVAILABLE")

    def test_event_groups_never_cross_temporal_partitions(self):
        dates = pd.Series(pd.date_range("2024-01-01", periods=12, tz="UTC"))
        features = pd.DataFrame({"x": range(12)})
        target = pd.Series([0, 1] * 6)
        groups = pd.Series(["", "", "", "", "", "", "", "storm-x", "storm-x", "", "", ""])
        x_train, x_valid, x_test = MLDataset.split(features, target, dates, groups)[:3]
        partitions = [set(frame.index) for frame in (x_train, x_valid, x_test)]
        self.assertTrue(any({7, 8}.issubset(partition) for partition in partitions))
        self.assertFalse(any({7, 8} & left and {7, 8} & right for left in partitions for right in partitions if left is not right))

    def test_model_registry_promotes_and_rolls_back_atomically(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate"
            candidate.mkdir()
            flood = candidate / "flood.joblib"
            cyclone = candidate / "cyclone.joblib"
            flood.write_bytes(b"flood-v1")
            cyclone.write_bytes(b"cyclone-v1")
            registry = ModelRegistry(root / "models")
            registry.register({"flood": flood, "cyclone": cyclone}, {}, release_id="r1")
            registry.promote("r1")
            flood.write_bytes(b"flood-v2")
            cyclone.write_bytes(b"cyclone-v2")
            registry.register({"flood": flood, "cyclone": cyclone}, {}, release_id="r2")
            registry.promote("r2")
            self.assertEqual(registry.active_model_path("flood").read_bytes(), b"flood-v2")
            registry.rollback()
            self.assertEqual(registry.active_model_path("flood").read_bytes(), b"flood-v1")

    def test_quarantined_registry_never_uses_legacy_fallback(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fallback = root / "legacy.joblib"
            fallback.write_bytes(b"legacy")
            registry = ModelRegistry(root / "models")
            registry.deactivate("quality gate failed")
            with self.assertRaisesRegex(FileNotFoundError, "quality gate failed"):
                registry.active_model_path("flood", fallback)

    def test_api_middleware_adds_request_id_and_limits_bodies(self):
        with patch.dict(
            "os.environ",
            {"SUSBIOME_MAX_REQUEST_BYTES": "4", "SUSBIOME_RATE_LIMIT_PER_MINUTE": "10"},
        ):
            app = FastAPI()
            configure_middleware(app)

            @app.post("/echo")
            def echo():
                return {"ok": True}

            client = TestClient(app)
            response = client.post("/echo", headers={"X-Request-ID": "test-request"})
            self.assertEqual(response.headers["X-Request-ID"], "test-request")
            oversized = client.post("/echo", content=b"12345")
            self.assertEqual(oversized.status_code, 413)

    def test_collection_gate_blocks_incomplete_archives(self):
        with patch(
            "scripts.production_pipeline.ingestion_status",
            return_value={"era5_valid_months": 239, "gpm_days": 7305},
        ):
            complete, _ = collection_complete()
        self.assertFalse(complete)

    def test_readiness_uses_service_unavailable_status(self):
        response = Response()
        with patch("scripts.api.routers.health.ready", return_value=False):
            payload = readiness(response)
        self.assertFalse(payload["ready"])
        self.assertEqual(response.status_code, 503)

    def test_dependency_status_includes_operational_monitoring(self):
        with patch(
            "scripts.api.dependencies.operational_status",
            return_value={"healthy": True},
        ):
            status = dependency_status()
        self.assertTrue(status["operations"])

    def test_dependency_status_explains_unhealthy_operations(self):
        with patch(
            "scripts.api.dependencies.operational_status",
            return_value={"healthy": False, "findings": ["No refresh record exists."]},
        ):
            status = dependency_status()
        self.assertFalse(status["operations"])
        self.assertEqual(dependency_errors()["operations"], "No refresh record exists.")

    def test_district_registry_covers_all_northeast_states(self):
        locations = DashboardLoader.locations()
        self.assertEqual(len(locations), 133)
        self.assertEqual(locations["state"].nunique(), 8)
        self.assertIn("Bichom", locations["district"].tolist())
        self.assertIn("Meluri", locations["district"].tolist())

    def test_dashboard_filters_to_district_grid_cell(self):
        risk = pd.DataFrame(
            {
                "valid_time": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-01"], utc=True),
                "latitude": [27.0, 27.0, 26.0],
                "longitude": [93.5, 93.5, 92.0],
            }
        )
        location = pd.Series(
            {"state": "Arunachal Pradesh", "district": "Itanagar Capital Complex", "latitude": 27.084, "longitude": 93.605}
        )
        filtered = DashboardLoader.filter_district(risk, location)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered["latitude"].unique().tolist(), [27.0])

    def test_ground_truth_normalizes_mixed_schema_types(self):
        frame = pd.DataFrame(
            {
                "schema_version": [1.0, "1.0"],
                "verified": ["yes", False],
                "collected_at": ["2024-01-01", pd.Timestamp("2024-01-02", tz="UTC")],
            }
        )
        result = normalize(frame)
        self.assertEqual(result["schema_version"].tolist(), ["1.0", "1.0"])
        self.assertEqual(result["verified"].tolist(), [True, False])
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["collected_at"]))

    def test_gdacs_polygon_containment_respects_holes(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [
                [[90, 20], [100, 20], [100, 30], [90, 30], [90, 20]],
                [[94, 24], [96, 24], [96, 26], [94, 26], [94, 24]],
            ],
        }
        self.assertTrue(_geometry_contains(geometry, 92, 25))
        self.assertFalse(_geometry_contains(geometry, 95, 25))
        self.assertFalse(_geometry_contains(geometry, 101, 25))

    def test_canonical_features_include_day_of_year(self):
        self.assertIn("day_of_year", FEATURE_COLUMNS)
        self.assertEqual(len(FEATURE_COLUMNS), len(set(FEATURE_COLUMNS)))

    def test_single_negative_class_has_zero_positive_probability(self):
        values = pd.DataFrame({"x": [1, 2, 3]})
        result = PredictionInference.probability(
            SingleClassModel(), values, values.index, "probability"
        )
        self.assertEqual(result.tolist(), [0.0, 0.0, 0.0])

    def test_api_rejects_paths_outside_data(self):
        with self.assertRaises(ValueError):
            resolve_data_path(Path("/tmp/private.parquet"), default=DEFAULT_FEATURE_FILE)

    def test_longitudes_and_region_are_normalized(self):
        dataframe = pd.DataFrame(
            {
                "latitude": [26.0, 40.0],
                "longitude": [450.0, 90.0],
                "valid_time": pd.to_datetime(["2024-01-01", "2024-01-01"], utc=True),
                "value": [1.0, 2.0],
            }
        )
        aligned = DataAligner().align(dataframe)
        self.assertEqual(len(aligned), 1)
        self.assertEqual(float(aligned.iloc[0]["longitude"]), 90.0)

    def test_production_features_reject_one_day(self):
        dataframe = pd.DataFrame(
            {
                "latitude": [26.0],
                "longitude": [92.0],
                "valid_time": pd.to_datetime(["2024-01-01"], utc=True),
                "precipitation": [10.0],
                "value": [298.0],
            }
        )
        with self.assertRaisesRegex(ValueError, "at least 90 distinct days"):
            FeatureEngineering(require_history=True).build(dataframe)

    def test_training_rejects_proxy_label_provenance(self):
        rows = 3650
        dataframe = pd.DataFrame(
            {
                "latitude": [26.0] * rows,
                "longitude": [92.0] * rows,
                "valid_time": pd.date_range("2024-01-01", periods=rows, tz="UTC"),
                "label_method": ["weather_threshold_proxy"] * rows,
                "flood_risk": [0, 1] * (rows // 2),
            }
        )
        for column in FEATURE_COLUMNS:
            dataframe[column] = 1.0
        with self.assertRaisesRegex(ValueError, "verified event labels"):
            MLDataset.validate_training_quality(dataframe, target="flood_risk")

    def test_temporal_split_has_no_date_overlap(self):
        dates = pd.Series(pd.date_range("2024-01-01", periods=100, tz="UTC"))
        features = pd.DataFrame({"x": range(100)})
        target = pd.Series([0, 1] * 50)
        split = MLDataset.split(features, target, dates)
        x_train, x_valid, x_test = split[:3]
        self.assertLess(x_train.index.max(), x_valid.index.min())
        self.assertLess(x_valid.index.max(), x_test.index.min())

    def test_model_contract_requires_metadata(self):
        with self.assertRaisesRegex(ValueError, "missing SusBiome metadata"):
            PredictionLoader.validate_estimator(
                ContractModel(), path=Path("model.joblib")
            )

    def test_model_contract_rejects_research_only_artifact(self):
        model = ContractModel()
        model.susbiome_metadata_ = {
            "schema_version": 1,
            "feature_columns": FEATURE_COLUMNS,
            "label_method": "verified_event_alignment",
            "production_eligible": False,
            "target": "flood_risk",
            "metrics": {},
        }
        with self.assertRaisesRegex(ValueError, "ineligible for production"):
            PredictionLoader.validate_estimator(model, path=Path("model.joblib"))

    def test_risk_rejects_invalid_probability(self):
        dataframe = pd.DataFrame(
            {
                "flood_prediction": [1],
                "drought_prediction": [0],
                "cyclone_prediction": [0],
                "flood_probability": [1.2],
                "drought_probability": [0.0],
                "cyclone_probability": [0.0],
            }
        )
        with self.assertRaises(ValueError):
            validate_prediction_values(dataframe)

    def test_no_risk_has_no_dominant_hazard(self):
        self.assertEqual(CombinedRisk.dominant_hazard(0, 0, 0), "None")

    def test_gdelt_integer_date_is_not_parsed_as_epoch(self):
        self.assertEqual(parse_event_date(20150501).isoformat(), "2015-05-01")

    def test_unknown_gdelt_text_is_not_defaulted_to_flood(self):
        hazard, subtype, keyword = classify_event("routine political meeting")
        self.assertIsNone(hazard)
        self.assertIsNone(subtype)
        self.assertEqual(keyword, "")

    def test_era5_request_is_regional_and_complete(self):
        request = era5_request(2024, 2)
        self.assertEqual(request["area"], [30.5, 87.0, 20.0, 98.5])
        self.assertEqual(len(request["day"]), 29)
        self.assertEqual(len(request["time"]), 24)

    def test_era5_request_supports_partial_current_month(self):
        request = era5_request(2026, 6, start_day=1, end_day=28)

        self.assertEqual(request["day"][0], "01")
        self.assertEqual(request["day"][-1], "28")
        self.assertEqual(len(request["day"]), 28)

    def test_historical_fusion_prefers_gpm_precipitation(self):
        keys = {
            "valid_time": pd.to_datetime(["2024-01-01"], utc=True),
            "latitude": [26.0],
            "longitude": [92.0],
        }
        era5 = pd.DataFrame({**keys, "precipitation_era5": [2.0], "temperature": [298.0]})
        gpm = pd.DataFrame({**keys, "precipitation_gpm": [3.0]})
        result = fuse_frames(era5, gpm)
        self.assertEqual(float(result.iloc[0]["precipitation"]), 3.0)

    def test_historical_fusion_falls_back_to_era5_precipitation(self):
        keys = {
            "valid_time": pd.to_datetime(["2025-10-01"], utc=True),
            "latitude": [26.0],
            "longitude": [92.0],
        }
        era5 = pd.DataFrame(
            {**keys, "precipitation_era5": [2.5], "temperature": [298.0]}
        )
        gpm = pd.DataFrame(
            {
                "valid_time": pd.to_datetime(["2025-09-30"], utc=True),
                "latitude": [26.0],
                "longitude": [92.0],
                "precipitation_gpm": [1.0],
            }
        )
        result = fuse_frames(era5, gpm)
        self.assertEqual(float(result.iloc[0]["precipitation"]), 2.5)
        self.assertEqual(result.iloc[0]["precipitation_source"], "ERA5")

    def test_verified_events_align_to_grid_and_window(self):
        weather = pd.DataFrame(
            {
                "valid_time": pd.date_range("2024-01-01", periods=3, tz="UTC"),
                "latitude": [26.0] * 3,
                "longitude": [92.0] * 3,
            }
        )
        events = pd.DataFrame(
            {
                "event_date": ["2024-01-02"],
                "hazard_type": ["FLOOD"],
                "state": ["Assam"],
                "latitude": [26.0],
                "longitude": [92.0],
                "verified": [True],
                "confidence": [90],
            }
        )
        accepted, rejected = prepare_events(events)
        result, matched = align_events(weather, accepted)
        self.assertTrue(rejected.empty)
        self.assertEqual(matched, 3)
        self.assertEqual(int(result["flood_risk"].sum()), 3)

    def test_hazard_features_cover_model_schema(self):
        days = 10
        frame = pd.DataFrame(
            {
                "valid_time": pd.date_range("2024-01-01", periods=days, tz="UTC"),
                "latitude": [26.0] * days,
                "longitude": [92.0] * days,
                "precipitation": range(days),
                "temperature": [298.0] * days,
                "temperature_min": [295.0] * days,
                "temperature_max": [301.0] * days,
                "relative_humidity": [80.0] * days,
                "surface_pressure_hpa": [1000.0] * days,
                "wind_speed": [2.0] * days,
                "wind_speed_max": [4.0] * days,
                "soil_moisture_surface": [0.3] * days,
                "runoff": [1.0] * days,
                "potential_evaporation": [2.0] * days,
            }
        )
        result = build_features(frame)
        self.assertFalse(result[FEATURE_COLUMNS].isna().any().any())
        self.assertEqual(float(result.iloc[-1]["precipitation_3d_sum"]), 24.0)

    def test_inference_uses_registered_threshold(self):
        values = pd.DataFrame({"x": [1, 2]})
        self.assertEqual(
            PredictionInference.classify(ThresholdModel(), values).tolist(),
            [0, 1],
        )

    def test_production_api_requires_key(self):
        with patch.dict("os.environ", {"SUSBIOME_ENV": "production", "SUSBIOME_API_KEY": "secret"}):
            with self.assertRaises(Exception):
                require_api_key("wrong")
            self.assertIsNone(require_api_key("secret"))

    def test_drift_monitor_detects_large_shift(self):
        reference = pd.DataFrame({column: np.arange(100) for column in FEATURE_COLUMNS})
        current = pd.DataFrame({column: np.arange(100) + 1000 for column in FEATURE_COLUMNS})
        self.assertTrue(drift_report(reference, current)["drift_detected"])


if __name__ == "__main__":
    unittest.main()
