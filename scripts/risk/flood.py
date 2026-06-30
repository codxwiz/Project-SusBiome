"""
==============================================================
Project SusBiome
Flood Risk Engine
==============================================================

Converts Flood Model predictions into standardized
Flood Risk scores and levels.

Responsibilities
----------------
• Validate prediction dataset
• Compute flood risk score
• Compute flood risk level
• Append risk columns

This module contains NO machine learning logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.risk.models import (
    HIGH,
    HIGH_THRESHOLD,
    LOW,
    LOW_THRESHOLD,
    MODERATE,
    MODERATE_THRESHOLD,
    NONE,
    NONE_THRESHOLD,
    REQUIRED_COLUMNS,
    EXTREME,
    score_to_level,
    validate_prediction_values,
)

logger = logging.getLogger(__name__)


class FloodRisk:
    """
    Flood Risk Engine.
    """

    # ======================================================
    # VALIDATE
    # ======================================================

    @staticmethod
    def validate(
        dataframe: pd.DataFrame,
    ) -> None:
        """
        Validate prediction dataset.
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
                "Prediction dataset is empty."
            )

        missing = [

            column

            for column in REQUIRED_COLUMNS

            if column not in dataframe.columns

        ]

        if missing:

            raise ValueError(

                "Missing required columns: "

                + ", ".join(missing)

            )

        validate_prediction_values(dataframe)

    # ======================================================
    # SCORE
    # ======================================================

    @staticmethod
    def score(
        prediction: int,
        probability: float,
    ) -> int:
        """
        Calculate flood risk score.
        """

        #
        # Negative prediction
        #

        if prediction == 0:

            return NONE

        #
        # Positive prediction
        #

        if probability < NONE_THRESHOLD:

            return NONE

        if probability < LOW_THRESHOLD:

            return LOW

        if probability < MODERATE_THRESHOLD:

            return MODERATE

        if probability < HIGH_THRESHOLD:

            return HIGH

        return EXTREME

    # ======================================================
    # BUILD
    # ======================================================

    def build(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Build flood risk.
        """

        self.validate(
            dataframe,
        )

        logger.info(
            "Calculating flood risk."
        )

        dataframe = dataframe.copy()

        dataframe["flood_risk_score"] = [

            self.score(

                prediction,

                probability,

            )

            for prediction, probability

            in zip(

                dataframe[
                    "flood_prediction"
                ],

                dataframe[
                    "flood_probability"
                ],

            )

        ]

        dataframe["flood_risk_level"] = (

            dataframe[
                "flood_risk_score"
            ]

            .map(
                score_to_level
            )

        )

        logger.info(
            "Flood risk complete."
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
        Flood risk summary.
        """

        counts = (

            dataframe[
                "flood_risk_level"
            ]

            .value_counts()

            .to_dict()

        )

        return {

            "rows": len(
                dataframe,
            ),

            "distribution": counts,

        }
