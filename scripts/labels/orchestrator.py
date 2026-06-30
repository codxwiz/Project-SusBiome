"""
============================================================
Label Engineering Orchestrator
============================================================

Runs the complete Label Engineering pipeline.

Pipeline

Features
    ↓
Load
    ↓
Label Engineering
    ↓
Save Training Dataset

============================================================
"""

from __future__ import annotations

import logging

from pathlib import Path

import pandas as pd

from scripts.labels.engineering import LabelEngineering

from scripts.labels.models import (
    DEFAULT_INPUT,
    DEFAULT_OUTPUT,
)

logger = logging.getLogger(
    "susbiome.labels.orchestrator"
)

if not logger.handlers:

    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()

    console.setFormatter(

        logging.Formatter(

            "%(asctime)s | %(levelname)s | %(message)s"

        )

    )

    logger.addHandler(console)


# ==========================================================
# LABEL ORCHESTRATOR
# ==========================================================

class LabelOrchestrator:
    """
    Coordinate the complete label engineering pipeline.
    """

    def __init__(
        self,
    ) -> None:

        self.engineering = LabelEngineering()

        logger.info(
            "Label Orchestrator initialized."
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
    ) -> Path:

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

        return path

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
        Execute the complete label engineering pipeline.
        """

        logger.info(
            "Starting Label Engineering."
        )

        #
        # Load feature dataset
        #

        dataframe = self.load(
            input_path
        )

        #
        # Build labels
        #

        dataframe = self.engineering.build(
            dataframe
        )

        #
        # Save training dataset
        #

        output = self.save(

            dataframe,

            output_path,

        )

        logger.info(
            "Label Engineering completed."
        )

        return output