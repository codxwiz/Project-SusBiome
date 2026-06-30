"""
==============================================================
Project SusBiome
Combined Risk Engine
==============================================================

Combines Flood, Drought and Cyclone risks into a
single Overall Risk assessment.

Responsibilities
----------------
• Validate risk dataset
• Calculate overall risk score
• Calculate overall risk level
• Identify dominant hazard
• Append combined risk columns

This module contains NO machine learning logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.risk.models import (
    RISK_SCORE_COLUMNS,
    score_to_level,
)

logger = logging.getLogger(__name__)


class CombinedRisk:
    """
    Combined Risk Engine.
    """

    # ======================================================
    # REQUIRED INPUT
    # ======================================================

    REQUIRED_COLUMNS = [

        "flood_risk_score",

        "drought_risk_score",

        "cyclone_risk_score",

    ]

    # ======================================================
    # VALIDATE
    # ======================================================

    @classmethod
    def validate(
        cls,
        dataframe: pd.DataFrame,
    ) -> None:
        """
        Validate risk dataset.
        """

        if not isinstance(
            dataframe,
            pd.DataFrame,
        ):
            raise TypeError(
                "Input must be a pandas DataFrame."
            )

        if dataframe.empty:
            raise ValueError(
                "Risk dataset is empty."
            )

        missing = [

            column

            for column in cls.REQUIRED_COLUMNS

            if column not in dataframe.columns

        ]

        if missing:

            raise ValueError(

                "Missing required columns: "

                + ", ".join(missing)

            )

    # ======================================================
    # SCORE
    # ======================================================

    @staticmethod
    def score(
        flood: int,
        drought: int,
        cyclone: int,
    ) -> int:
        """
        Calculate overall risk score.

        Current strategy:
        Overall score = maximum hazard score.
        """

        return max(

            flood,

            drought,

            cyclone,

        )

    # ======================================================
    # DOMINANT HAZARD
    # ======================================================

    @staticmethod
    def dominant_hazard(
        flood: int,
        drought: int,
        cyclone: int,
    ) -> str:
        """
        Determine dominant hazard.
        """

        if max(flood, drought, cyclone) == 0:
            return "None"

        hazards = {

            "Flood": flood,

            "Drought": drought,

            "Cyclone": cyclone,

        }

        return max(

            hazards,

            key=hazards.get,

        )

    # ======================================================
    # BUILD
    # ======================================================

    def build(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Build combined risk.
        """

        self.validate(
            dataframe,
        )

        logger.info(
            "Calculating combined risk."
        )

        dataframe = dataframe.copy()

        dataframe["overall_risk_score"] = [

            self.score(

                flood,

                drought,

                cyclone,

            )

            for flood, drought, cyclone

            in zip(

                dataframe["flood_risk_score"],

                dataframe["drought_risk_score"],

                dataframe["cyclone_risk_score"],

            )

        ]

        dataframe["overall_risk_level"] = (

            dataframe[
                "overall_risk_score"
            ]

            .map(
                score_to_level
            )

        )

        dataframe["dominant_hazard"] = [

            self.dominant_hazard(

                flood,

                drought,

                cyclone,

            )

            for flood, drought, cyclone

            in zip(

                dataframe["flood_risk_score"],

                dataframe["drought_risk_score"],

                dataframe["cyclone_risk_score"],

            )

        ]

        logger.info(
            "Combined risk complete."
        )

        return dataframe

    # ======================================================
    # SUMMARY
    # ======================================================

    @staticmethod
    def summary(
        dataframe: pd.DataFrame,
    ) -> dict:
        """
        Combined risk summary.
        """

        summary = {

            "rows": len(
                dataframe,
            ),

            "overall_distribution": (

                dataframe[
                    "overall_risk_level"
                ]

                .value_counts()

                .to_dict()

            ),

            "dominant_hazards": (

                dataframe[
                    "dominant_hazard"
                ]

                .value_counts()

                .to_dict()

            ),

            "maximum_risk": int(

                dataframe[
                    "overall_risk_score"
                ].max()

            ),

            "mean_risk": float(

                dataframe[
                    "overall_risk_score"
                ].mean()

            ),

        }

        return summary

    # ======================================================
    # AVAILABLE SCORES
    # ======================================================

    @staticmethod
    def score_columns() -> list[str]:
        """
        Return available risk score columns.
        """

        return RISK_SCORE_COLUMNS.copy()
