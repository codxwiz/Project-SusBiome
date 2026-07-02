"""
==============================================================
Project SusBiome
Prediction Model Loader
==============================================================

Loads trained Machine Learning models from disk.

Responsibilities
----------------
• Load Flood model
• Load Drought model
• Load Cyclone model
• Validate model files
• Cache loaded models
• Provide a single access point for inference

This module contains NO prediction logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
from scripts.ml.evaluation import model_quality_findings
from scripts.ml.registry import ModelRegistry

from scripts.prediction.models import (
    CYCLONE_MODEL,
    DROUGHT_MODEL,
    FLOOD_MODEL,
    SUPPORTED_EXTENSIONS,
    FEATURE_COLUMNS,
)

logger = logging.getLogger(__name__)


class PredictionLoader:
    """
    Load trained machine learning models.

    Models are loaded only once and cached in memory.
    """

    def __init__(
        self,
    ) -> None:

        self.flood: Any | None = None

        self.drought: Any | None = None

        self.cyclone: Any | None = None

        self.registry = ModelRegistry()

        logger.info(
            "Prediction Loader initialized."
        )

    # ======================================================
    # VALIDATE MODEL FILE
    # ======================================================

    @staticmethod
    def validate(
        path: Path,
    ) -> None:
        """
        Validate model file.
        """

        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "Model path must be pathlib.Path."
            )

        if not path.exists():
            raise FileNotFoundError(
                f"Model not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Not a file: {path}"
            )

        if path.suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported model format: {path.suffix}"
            )

    # ======================================================
    # LOAD SINGLE MODEL
    # ======================================================

    def load_model(
        self,
        path: Path,
    ) -> Any:
        """
        Load one model from disk.
        """

        self.validate(
            path,
        )

        logger.info(
            "Loading model: %s",
            path.name,
        )

        model = joblib.load(
            path,
        )

        self.validate_estimator(model, path=path)

        logger.info(
            "Loaded model: %s",
            path.name,
        )

        return model

    @staticmethod
    def validate_estimator(model: Any, *, path: Path) -> None:
        """Validate the contract required by production inference."""
        for method in ("predict", "predict_proba"):
            if not callable(getattr(model, method, None)):
                raise ValueError(f"Model {path.name} does not implement {method}().")

        fitted_features = list(getattr(model, "feature_names_in_", []))
        if fitted_features != FEATURE_COLUMNS:
            raise ValueError(
                f"Model {path.name} feature schema does not match the application."
            )

        classes = set(getattr(model, "classes_", []))
        if classes != {0, 1}:
            raise ValueError(
                f"Model {path.name} must be trained with classes 0 and 1; "
                f"found {sorted(classes)}."
            )

        metadata = getattr(model, "susbiome_metadata_", None)
        if not isinstance(metadata, dict):
            raise ValueError(f"Model {path.name} is missing SusBiome metadata.")
        if metadata.get("schema_version") != 1:
            raise ValueError(f"Model {path.name} has an unsupported schema version.")
        if metadata.get("feature_columns") != FEATURE_COLUMNS:
            raise ValueError(f"Model {path.name} metadata has the wrong feature schema.")
        if metadata.get("label_method") != "verified_event_alignment":
            raise ValueError(f"Model {path.name} was not trained on verified event labels.")
        if metadata.get("production_eligible") is not True:
            raise ValueError(f"Model {path.name} is explicitly ineligible for production.")
        target = str(metadata.get("target", ""))
        hazard = target.removesuffix("_risk")
        findings = model_quality_findings(hazard, metadata.get("metrics", {}))
        if findings:
            raise ValueError(
                f"Model {path.name} failed the production quality gate: " + "; ".join(findings)
            )

    # ======================================================
    # LOAD FLOOD MODEL
    # ======================================================

    def load_flood(
        self,
    ) -> Any:

        if self.flood is None:

            self.flood = self.load_model(
                self.registry.active_model_path("flood", FLOOD_MODEL),
            )

        return self.flood

    # ======================================================
    # LOAD DROUGHT MODEL
    # ======================================================

    def load_drought(
        self,
    ) -> Any:

        if self.drought is None:

            self.drought = self.load_model(
                self.registry.active_model_path("drought", DROUGHT_MODEL),
            )

        return self.drought

    # ======================================================
    # LOAD CYCLONE MODEL
    # ======================================================

    def load_cyclone(
        self,
    ) -> Any:

        if self.cyclone is None:

            self.cyclone = self.load_model(
                self.registry.active_model_path("cyclone", CYCLONE_MODEL),
            )

        return self.cyclone

    # ======================================================
    # LOAD ALL
    # ======================================================

    def load_all(
        self,
    ) -> dict[str, Any]:
        """
        Load every trained model.
        """

        logger.info(
            "Loading all prediction models."
        )

        models = {
            "flood": self.load_flood(),
            "cyclone": self.load_cyclone(),
        }
        try:
            models["drought"] = self.load_drought()
        except Exception as error:
            models["drought"] = None
            logger.warning("Experimental drought model unavailable: %s", error)
        return models

    # ======================================================
    # CLEAR CACHE
    # ======================================================

    def clear(
        self,
    ) -> None:
        """
        Remove cached models from memory.
        """

        self.flood = None

        self.drought = None

        self.cyclone = None

        logger.info(
            "Prediction model cache cleared."
        )

    # ======================================================
    # STATUS
    # ======================================================

    def status(
        self,
    ) -> dict[str, bool]:
        """
        Return cache status.
        """

        return {

            "flood": self.flood is not None,

            "drought": self.drought is not None,

            "cyclone": self.cyclone is not None,

        }

    # ======================================================
    # READY
    # ======================================================

    def ready(
        self,
    ) -> bool:
        """
        Check whether all models are loaded.
        """

        status = self.status()
        return status["flood"] and status["cyclone"]
