"""
============================================================
Machine Learning Orchestrator
============================================================

Runs the complete Machine Learning pipeline.

Pipeline

Feature Dataset
        ↓
Training
        ↓
Saved Models
        ↓
Prediction

============================================================
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from scripts.ml.trainer import MLTrainer
from scripts.ml.predictor import MLPredictor

logger = logging.getLogger(
    "susbiome.ml.orchestrator"
)

if not logger.handlers:

    logger.setLevel(
        logging.INFO
    )

    console = logging.StreamHandler()

    console.setFormatter(

        logging.Formatter(

            "%(asctime)s | %(levelname)s | %(message)s"

        )

    )

    logger.addHandler(
        console
    )


# ==========================================================
# MACHINE LEARNING ORCHESTRATOR
# ==========================================================

class MLOrchestrator:
    """
    Coordinates the Machine Learning pipeline.
    """

    def __init__(
        self,
    ) -> None:

        self.trainer = MLTrainer()

        logger.info(
            "Machine Learning Orchestrator initialized."
        )

    # ======================================================
    # LOAD
    # ======================================================

    @staticmethod
    def load(
        path: Path,
    ) -> pd.DataFrame:

        logger.info(
            "Loading %s",
            path,
        )

        return pd.read_parquet(
            path
        )

    # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
        *,
        dataset_path: Path,
    ) -> tuple[dict, pd.DataFrame]:
        """
        Train all models and generate predictions.

        Returns
        -------
        (metrics, prediction_dataframe)
        """

        logger.info(
            "Starting Machine Learning pipeline."
        )

        #
        # Train models
        #

        metrics = self.trainer.train(

            dataset_path=dataset_path,

        )

        #
        # Load trained models
        #

        predictor = MLPredictor()

        #
        # Load feature dataset
        #

        dataframe = self.load(

            dataset_path

        )

        #
        # Remove target columns if present
        #

        dataframe = dataframe.drop(

            columns=[

                "flood_risk",

                "drought_risk",

                "cyclone_risk",

            ],

            errors="ignore",

        )

        #
        # Predict
        #

        predictions = predictor.predict(

            dataframe

        )

        logger.info(
            "Machine Learning pipeline completed."
        )

        return (

            metrics,

            predictions,

        )