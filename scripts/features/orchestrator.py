"""
============================================================
Feature Engineering Orchestrator
============================================================

Runs the complete Feature Engineering pipeline.

Pipeline

Unified Dataset
        ↓
Feature Engineering
        ↓
Gold Dataset

============================================================
"""

from __future__ import annotations

import logging

from pathlib import Path

import pandas as pd

from scripts.features.engineering import (
    FeatureEngineering,
)
from scripts.features.models import DEFAULT_INPUT, DEFAULT_OUTPUT

logger = logging.getLogger(
    "susbiome.features.orchestrator"
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
# FEATURE ENGINEERING ORCHESTRATOR
# ==========================================================

class FeatureEngineeringOrchestrator:
    """
    Runs the complete Feature Engineering pipeline.
    """

    def __init__(
        self,
    ) -> None:

        self.engineering = FeatureEngineering(require_history=True)

        logger.info(

            "Feature Engineering Orchestrator initialized."

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
    # SAVE
    # ======================================================

    @staticmethod
    def save(
        dataframe: pd.DataFrame,
        path: Path,
    ) -> None:

        path.parent.mkdir(

            parents=True,

            exist_ok=True,

        )

        dataframe.to_parquet(

            path,

            index=False,

        )

        logger.info(

            "Saved %s",

            path,

        )

    # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
        *,
        input_path: Path = DEFAULT_INPUT,
        output_path: Path = DEFAULT_OUTPUT,
    ) -> Path:
        """
        Execute Feature Engineering.
        """

        logger.info(

            "Starting Feature Engineering."

        )

        dataframe = self.load(

            input_path

        )

        dataframe = self.engineering.build(

            dataframe

        )

        self.save(

            dataframe,

            output_path,

        )

        logger.info(

            "Feature Engineering complete."

        )

        return output_path
