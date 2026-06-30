"""
==============================================================
Project SusBiome
Risk Formatter
==============================================================

Formats the complete Risk Engine output into a
standardized dataset for APIs, dashboards and exports.

Responsibilities
----------------
• Validate risk dataset
• Reorder columns
• Round probabilities
• Sort output
• Generate summary
• Produce standardized risk dataset

This module contains NO machine learning logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.risk.models import (
    METADATA_COLUMNS,
    PREDICTION_COLUMNS,
    PROBABILITY_COLUMNS,
    RISK_SCORE_COLUMNS,
    RISK_LEVEL_COLUMNS,
)

logger = logging.getLogger(__name__)


class RiskFormatter:
    """
    Format Risk Engine output.
    """

    # ======================================================
    # VALIDATE
    # ======================================================

    @staticmethod
    def validate(
        dataframe: pd.DataFrame,
    ) -> None:
        """
        Validate risk dataframe.
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
                "Risk dataframe is empty."
            )

        required = (

            METADATA_COLUMNS

            + RISK_SCORE_COLUMNS

            + RISK_LEVEL_COLUMNS

        )

        missing = [

            column

            for column in required

            if column not in dataframe.columns

        ]

        if missing:

            raise ValueError(

                "Missing required columns: "

                + ", ".join(missing)

            )

    # ======================================================
    # ROUND
    # ======================================================

    @staticmethod
    def round_probabilities(
        dataframe: pd.DataFrame,
        digits: int = 4,
    ) -> pd.DataFrame:
        """
        Round probability columns.
        """

        dataframe = dataframe.copy()

        for column in PROBABILITY_COLUMNS:

            if column in dataframe.columns:

                dataframe[column] = (

                    dataframe[column]

                    .round(digits)

                )

        return dataframe

    # ======================================================
    # SORT
    # ======================================================

    @staticmethod
    def sort(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Sort dataset.
        """

        dataframe = dataframe.copy()

        dataframe = dataframe.sort_values(

            by=[

                "valid_time",

                "latitude",

                "longitude",

            ],

            ignore_index=True,

        )

        return dataframe

    # ======================================================
    # REORDER
    # ======================================================

    @staticmethod
    def reorder(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Standardize column order.
        """

        dataframe = dataframe.copy()

        ordered = []

        #
        # Metadata
        #

        ordered.extend(

            [

                column

                for column in METADATA_COLUMNS

                if column in dataframe.columns

            ]

        )

        #
        # Predictions
        #

        ordered.extend(

            [

                column

                for column in PREDICTION_COLUMNS

                if column in dataframe.columns

            ]

        )

        #
        # Probabilities
        #

        ordered.extend(

            [

                column

                for column in PROBABILITY_COLUMNS

                if column in dataframe.columns

            ]

        )

        #
        # Risk Scores
        #

        ordered.extend(

            [

                column

                for column in RISK_SCORE_COLUMNS

                if column in dataframe.columns

            ]

        )

        #
        # Risk Levels
        #

        ordered.extend(

            [

                column

                for column in RISK_LEVEL_COLUMNS

                if column in dataframe.columns

            ]

        )

        #
        # Dominant Hazard
        #

        if "dominant_hazard" in dataframe.columns:

            ordered.append(

                "dominant_hazard"

            )

        #
        # Remaining columns
        #

        ordered.extend(

            [

                column

                for column in dataframe.columns

                if column not in ordered

            ]

        )

        return dataframe.loc[

            :,

            ordered,

        ]

    # ======================================================
    # FORMAT
    # ======================================================

    def format(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Format risk dataset.
        """

        logger.info(
            "Formatting risk dataset."
        )

        self.validate(
            dataframe,
        )

        dataframe = self.round_probabilities(
            dataframe,
        )

        dataframe = self.sort(
            dataframe,
        )

        dataframe = self.reorder(
            dataframe,
        )

        logger.info(
            "Risk formatting complete."
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
        Risk dataset summary.
        """

        RiskFormatter.validate(
            dataframe,
        )

        summary = {

            "rows": len(
                dataframe,
            ),

            "start_time": dataframe[
                "valid_time"
            ].min(),

            "end_time": dataframe[
                "valid_time"
            ].max(),

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

            "highest_risk": (

                dataframe[
                    "overall_risk_score"
                ].max()

            ),

            "average_risk": float(

                dataframe[
                    "overall_risk_score"
                ].mean()

            ),

        }

        return summary

    # ======================================================
    # REPORT
    # ======================================================

    def report(
        self,
        dataframe: pd.DataFrame,
    ) -> dict:
        """
        Generate formatted report.
        """

        dataframe = self.format(
            dataframe,
        )

        return self.summary(
            dataframe,
        )