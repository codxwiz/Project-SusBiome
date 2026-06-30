"""
==============================================================
Project SusBiome
Risk Engine Orchestrator
==============================================================

Coordinates the complete Risk Engine pipeline.

Pipeline
--------
Prediction Dataset
        │
        ▼
Flood Risk
        │
        ▼
Drought Risk
        │
        ▼
Cyclone Risk
        │
        ▼
Combined Risk
        │
        ▼
Formatter
        │
        ▼
Final Risk Dataset

Responsibilities
----------------
• Load prediction dataset
• Execute all risk modules
• Format output
• Save results
• Generate summary

This module contains NO machine learning logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from scripts.risk.combined import CombinedRisk
from scripts.risk.cyclone import CycloneRisk
from scripts.risk.drought import DroughtRisk
from scripts.risk.flood import FloodRisk
from scripts.risk.formatter import RiskFormatter

logger = logging.getLogger(__name__)


class RiskOrchestrator:
    """
    End-to-end Risk Engine.
    """

    def __init__(
        self,
    ) -> None:

        self.flood = FloodRisk()

        self.drought = DroughtRisk()

        self.cyclone = CycloneRisk()

        self.combined = CombinedRisk()

        self.formatter = RiskFormatter()

        logger.info(
            "Risk Orchestrator initialized."
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

            raise FileNotFoundError(path)

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
        Save risk dataset.
        """

        path = Path(path)

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
    # BUILD
    # ======================================================

    def build(
        self,
        dataframe: pd.DataFrame,
    ) -> tuple[pd.DataFrame, dict]:
        """
        Build complete risk dataset.
        """

        logger.info(
            "Building risk dataset."
        )

        dataframe = self.flood.build(
            dataframe,
        )

        dataframe = self.drought.build(
            dataframe,
        )

        dataframe = self.cyclone.build(
            dataframe,
        )

        dataframe = self.combined.build(
            dataframe,
        )

        dataframe = self.formatter.format(
            dataframe,
        )

        summary = self.formatter.summary(
            dataframe,
        )

        logger.info(
            "Risk Engine completed."
        )

        return (

            dataframe,

            summary,

        )

    # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
        input_path: str | Path,
        output_path: str | Path,
    ) -> tuple[pd.DataFrame, dict]:
        """
        Execute complete Risk Engine.
        """

        logger.info(
            "Starting Risk Engine."
        )

        dataframe = self.load(
            input_path,
        )

        dataframe, summary = self.build(
            dataframe,
        )

        self.save(

            dataframe,

            output_path,

        )

        logger.info(
            "Risk pipeline completed."
        )

        return (

            dataframe,

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
        Generate risk report.
        """

        dataframe = self.formatter.format(
            dataframe,
        )

        return self.formatter.summary(
            dataframe,
        )