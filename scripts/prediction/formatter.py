"""
==============================================================
Project SusBiome
Prediction Formatter
==============================================================

Formats prediction results into a standardized dataset.

Responsibilities
----------------
• Validate prediction output
• Reorder columns
• Round probabilities
• Sort results
• Generate summary
• Prepare output for API/Dashboard

This module contains NO machine learning logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.prediction.models import (
    METADATA_COLUMNS,
    PREDICTION_COLUMNS,
    PROBABILITY_COLUMNS,
)

logger = logging.getLogger(__name__)


class PredictionFormatter:
    """
    Format prediction output.
    """

    # ======================================================
    # VALIDATE
    # ======================================================

    @staticmethod
    def validate(
        dataframe: pd.DataFrame,
    ) -> None:
        """
        Validate prediction dataframe.
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
                "Prediction dataframe is empty."
            )

        required = (

            METADATA_COLUMNS

            + PREDICTION_COLUMNS

        )

        missing = [

            column

            for column in required

            if column not in dataframe.columns

        ]

        if missing:

            raise ValueError(

                "Missing columns: "

                + ", ".join(missing)

            )

    # ======================================================
    # ROUND PROBABILITIES
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
        Sort prediction dataset.
        """

        dataframe = dataframe.copy()

        columns = [

            column

            for column in [

                "valid_time",

                "latitude",

                "longitude",

            ]

            if column in dataframe.columns

        ]

        if columns:

            dataframe = dataframe.sort_values(

                by=columns,

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
        Standardize output column order.
        """

        dataframe = dataframe.copy()

        ordered = []

        #
        # Metadata
        #

        for column in METADATA_COLUMNS:

            if column in dataframe.columns:

                ordered.append(
                    column
                )

        #
        # Prediction labels
        #

        for column in PREDICTION_COLUMNS:

            if column in dataframe.columns:

                ordered.append(
                    column
                )

        #
        # Probabilities
        #

        for column in PROBABILITY_COLUMNS:

            if column in dataframe.columns:

                ordered.append(
                    column
                )

        #
        # Remaining columns
        #

        for column in dataframe.columns:

            if column not in ordered:

                ordered.append(
                    column
                )

        return dataframe.loc[
            :,
            ordered,
        ]

    # ======================================================
    # SUMMARY
    # ======================================================

    @staticmethod
    def summary(
        dataframe: pd.DataFrame,
    ) -> dict:
        """
        Generate prediction summary.
        """

        PredictionFormatter.validate(
            dataframe,
        )

        summary = {

            "rows": len(
                dataframe,
            ),

            "flood_positive": int(

                dataframe[
                    "flood_prediction"
                ].sum()

            ),

            "drought_available": bool(
                dataframe.get("drought_available", pd.Series(True, index=dataframe.index)).all()
            ),

            "drought_positive": int(dataframe["drought_prediction"].sum()),

            "cyclone_positive": int(

                dataframe[
                    "cyclone_prediction"
                ].sum()

            ),

        }

        if "valid_time" in dataframe.columns:

            summary["start_time"] = (

                dataframe[
                    "valid_time"
                ].min()

            )

            summary["end_time"] = (

                dataframe[
                    "valid_time"
                ].max()

            )

        return summary

    # ======================================================
    # FORMAT
    # ======================================================

    def format(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Format prediction dataset.
        """

        logger.info(
            "Formatting prediction results."
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
            "Prediction formatting complete."
        )

        return dataframe

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
