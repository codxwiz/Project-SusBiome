"""
==============================================================
Project SusBiome
Drought Risk Engine
==============================================================

Converts Drought Model predictions into standardized
Drought Risk scores and levels.

Responsibilities
----------------
• Validate prediction dataset
• Compute drought risk score
• Compute drought risk level
• Append risk columns

This module contains NO machine learning logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.risk.models import (
    EXTREME,
    HIGH,
    HIGH_THRESHOLD,
    LOW,
    LOW_THRESHOLD,
    MODERATE,
    MODERATE_THRESHOLD,
    NONE,
    NONE_THRESHOLD,
    REQUIRED_COLUMNS,
    score_to_level,
    validate_prediction_values,
)

logger = logging.getLogger(__name__)


class DroughtRisk:
    """
    Drought Risk Engine.
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

        if not bool(
            dataframe.get("drought_available", pd.Series(True, index=dataframe.index)).all()
        ):
            return

        missing = [
            column
            for column in ("drought_prediction", "drought_probability")
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
        Calculate drought risk score.
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
        Build drought risk.
        """

        self.validate(
            dataframe,
        )

        logger.info(
            "Calculating drought risk."
        )

        dataframe = dataframe.copy()

        if not bool(
            dataframe.get("drought_available", pd.Series(True, index=dataframe.index)).all()
        ):
            dataframe["drought_risk_score"] = NONE
            dataframe["drought_risk_level"] = "UNAVAILABLE"
            return dataframe

        dataframe["drought_risk_score"] = [

            self.score(

                prediction,

                probability,

            )

            for prediction, probability

            in zip(

                dataframe[
                    "drought_prediction"
                ],

                dataframe[
                    "drought_probability"
                ],

            )

        ]

        dataframe["drought_risk_level"] = (

            dataframe[
                "drought_risk_score"
            ]

            .map(
                score_to_level
            )

        )

        logger.info(
            "Drought risk complete."
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
        Drought risk summary.
        """

        counts = (

            dataframe[
                "drought_risk_level"
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
