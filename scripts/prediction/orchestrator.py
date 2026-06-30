"""
==============================================================
Project SusBiome
Prediction Orchestrator
==============================================================

Coordinates the complete prediction pipeline.

Pipeline
--------
Input Dataset
        │
        ▼
Validation
        │
        ▼
Model Loader
        │
        ▼
Inference
        │
        ▼
Formatter
        │
        ▼
Prediction Output

Responsibilities
----------------
• Load prediction dataset
• Validate input
• Execute inference
• Format predictions
• Save predictions
• Generate summary

This module contains NO ML implementation.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from scripts.prediction.formatter import (
    PredictionFormatter,
)
from scripts.prediction.inference import (
    PredictionInference,
)

logger = logging.getLogger(__name__)


class PredictionOrchestrator:
    """
    End-to-end prediction pipeline.
    """

    def __init__(
        self,
    ) -> None:

        self.inference = PredictionInference()

        self.formatter = PredictionFormatter()

        logger.info(
            "Prediction Orchestrator initialized."
        )

    # ======================================================
    # LOAD
    # ======================================================

    @staticmethod
    def load(
        path: str | Path,
    ) -> pd.DataFrame:
        """
        Load prediction dataset.
        """

        path = Path(path)

        if not path.exists():

            raise FileNotFoundError(
                path
            )

        logger.info(
            "Loading %s",
            path,
        )

        if path.suffix == ".parquet":

            return pd.read_parquet(
                path,
            )

        if path.suffix == ".csv":

            return pd.read_csv(
                path,
                parse_dates=[
                    "valid_time",
                ],
            )

        raise ValueError(

            f"Unsupported file type: {path.suffix}"

        )

    # ======================================================
    # SAVE
    # ======================================================

    @staticmethod
    def save(
        dataframe: pd.DataFrame,
        path: str | Path,
    ) -> Path:
        """
        Save prediction output.
        """

        path = Path(path)

        path.parent.mkdir(

            parents=True,

            exist_ok=True,

        )

        logger.info(
            "Saving %s",
            path,
        )

        dataframe.to_parquet(

            path,

            index=False,

        )

        return path

    # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
        input_path: str | Path,
        output_path: str | Path,
        *,
        include_probability: bool = True,
    ) -> tuple[pd.DataFrame, dict]:

        logger.info(
            "Starting prediction pipeline."
        )

        dataframe = self.load(
            input_path,
        )

        predictions = self.inference.predict(

            dataframe,

            include_probability=include_probability,

        )

        predictions = self.formatter.format(

            predictions,

        )

        summary = self.formatter.summary(

            predictions,

        )

        self.save(

            predictions,

            output_path,

        )

        logger.info(
            "Prediction pipeline completed."
        )

        return (

            predictions,

            summary,

        )

    # ======================================================
    # RUN DATAFRAME
    # ======================================================

    def predict(
        self,
        dataframe: pd.DataFrame,
        *,
        include_probability: bool = True,
    ) -> tuple[pd.DataFrame, dict]:
        """
        Run prediction directly from a DataFrame.
        """

        logger.info(
            "Running in-memory prediction."
        )

        predictions = self.inference.predict(

            dataframe,

            include_probability=include_probability,

        )

        predictions = self.formatter.format(

            predictions,

        )

        summary = self.formatter.summary(

            predictions,

        )

        logger.info(
            "Prediction completed."
        )

        return (

            predictions,

            summary,

        )

    # ======================================================
    # REPORT
    # ======================================================

    def report(
        self,
        dataframe: pd.DataFrame,
    ) -> dict:
        """
        Generate prediction report.
        """

        dataframe = self.formatter.format(
            dataframe,
        )

        return self.formatter.summary(
            dataframe,
        )