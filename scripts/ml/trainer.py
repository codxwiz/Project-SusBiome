"""
============================================================
Machine Learning Trainer
============================================================

Coordinates training for all hazard models.

============================================================
"""

from __future__ import annotations

import logging
import json
import shutil
from uuid import uuid4
from datetime import UTC, datetime
from pathlib import Path

from scripts.ml.dataset import MLDataset

from scripts.ml.models import (
    TRAINING_DATASET,
    FLOOD_TARGET,
    DROUGHT_TARGET,
    CYCLONE_TARGET,
    FEATURE_COLUMNS,
)

from scripts.ml.flood import FloodModel
from scripts.ml.drought import DroughtModel
from scripts.ml.cyclone import CycloneModel
from scripts.ml.evaluation import evaluate_classifier, release_quality, select_threshold
from scripts.ml.registry import ModelRegistry
from scripts.ml.models import MODEL_DIRECTORY

logger = logging.getLogger(
    "susbiome.ml.trainer"
)


# ==========================================================
# MACHINE LEARNING TRAINER
# ==========================================================

class MLTrainer:

    """
    Coordinates all ML model training.
    """

    def __init__(
        self,
    ) -> None:

        self.flood = FloodModel()

        self.drought = DroughtModel()

        self.cyclone = CycloneModel()

        logger.info(
            "ML Trainer initialized."
        )

    # ======================================================
    # TRAIN ONE MODEL
    # ======================================================

    @staticmethod
    def train_model(
        *,
        dataset_path: Path,
        target: str,
        model,
        output_path: Path,
    ) -> dict:

        (
            X_train,
            X_valid,
            X_test,
            y_train,
            y_valid,
            y_test,
        ) = MLDataset.build(

            path=dataset_path,

            target=target,

        )

        model.train(

            X_train,

            y_train,

        )

        threshold = select_threshold(model.model, X_valid, y_valid)
        model.model.susbiome_threshold_ = threshold
        metrics = evaluate_classifier(
            model.model, X_test, y_test, threshold=threshold
        )

        model.model.susbiome_metadata_ = {
            "schema_version": 1,
            "target": target,
            "feature_columns": FEATURE_COLUMNS,
            "label_method": "verified_event_alignment",
            "trained_at": datetime.now(UTC).isoformat(),
            "metrics": metrics,
            "production_eligible": False,
        }

        model.save(output_path)

        return metrics

    # ======================================================
    # TRAIN
    # ======================================================

    def train(
        self,
        dataset_path: Path = TRAINING_DATASET,
    ) -> dict:

        logger.info(
            "Starting Machine Learning training."
        )

        results = {}
        release_id = (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{uuid4().hex[:8]}"
        )
        candidate_directory = MODEL_DIRECTORY / "candidates" / release_id
        candidate_directory.mkdir(parents=True, exist_ok=False)
        artifacts: dict[str, Path] = {}

        #
        # Flood
        #

        results["flood"] = self.train_model(

            dataset_path=dataset_path,

            target=FLOOD_TARGET,

            model=self.flood,
            output_path=candidate_directory / "flood_model.joblib",

        )
        artifacts["flood"] = candidate_directory / "flood_model.joblib"

        #
        # Drought
        #

        try:
            results["drought"] = self.train_model(
                dataset_path=dataset_path,
                target=DROUGHT_TARGET,
                model=self.drought,
                output_path=candidate_directory / "drought_model.joblib",
            )
            artifacts["drought"] = candidate_directory / "drought_model.joblib"
        except Exception as error:
            logger.warning("Experimental drought training skipped: %s", error)
            results["drought"] = {"status": "unavailable", "reason": str(error)}

        #
        # Cyclone
        #

        results["cyclone"] = self.train_model(

            dataset_path=dataset_path,

            target=CYCLONE_TARGET,

            model=self.cyclone,
            output_path=candidate_directory / "cyclone_model.joblib",

        )
        artifacts["cyclone"] = candidate_directory / "cyclone_model.joblib"

        logger.info(
            "Training complete."
        )

        quality = release_quality(results)
        quality["passed"] = False
        quality["findings"].append(
            "Legacy same-window event labels are research-only; production requires "
            "horizon-specific future targets and a matching serving contract."
        )
        registry = ModelRegistry()
        registered = registry.register(
            artifacts,
            {
                "training_dataset": str(dataset_path),
                "models": results,
                "quality_gate": quality,
            },
            release_id=release_id,
        )
        promoted = False
        if quality["passed"]:
            registry.promote(registered)
            promoted = True
        shutil.rmtree(candidate_directory)

        results["_release"] = {
            "release_id": registered,
            "promoted": promoted,
            "quality_gate": quality,
        }

        return results
