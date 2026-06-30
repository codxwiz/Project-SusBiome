"""
============================================================
Rolling Feature Engineering
============================================================

Computes rolling statistics for weather variables.

Input
-----
DataFrame

Output
------
DataFrame with rolling features added.

============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.features.models import (
    REQUIRED_COLUMNS,
    ROLLING_WINDOWS,
)

logger = logging.getLogger(
    "susbiome.features.rolling"
)

# ==========================================================
# ROLLING FEATURE ENGINEER
# ==========================================================


class RollingFeatureEngineer:
    """
    Computes rolling weather features.
    """

    def __init__(self) -> None:

        logger.info(
            "Rolling Feature Engineer initialized."
        )

    # ======================================================
    # VALIDATE
    # ======================================================

    @staticmethod
    def validate(
        dataframe: pd.DataFrame,
    ) -> None:
        """
        Validate required columns.
        """

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

    # ======================================================
    # SORT
    # ======================================================

    @staticmethod
    def sort(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Sort observations before rolling.
        """

        return dataframe.sort_values(

            [

                "latitude",

                "longitude",

                "valid_time",

            ]

        ).reset_index(

            drop=True

        )

    # ======================================================
    # ROLLING SUM
    # ======================================================

    @staticmethod
    def rolling_sum(
        dataframe: pd.DataFrame,
        *,
        column: str,
        window: int,
    ) -> pd.Series:

        return (

            dataframe

            .groupby(

                [

                    "latitude",

                    "longitude",

                ]

            )[column]

            .transform(

                lambda s:

                s.rolling(

                    window,

                    min_periods=1,

                ).sum()

            )

        )

    # ======================================================
    # ROLLING MEAN
    # ======================================================

    @staticmethod
    def rolling_mean(
        dataframe: pd.DataFrame,
        *,
        column: str,
        window: int,
    ) -> pd.Series:

        return (

            dataframe

            .groupby(

                [

                    "latitude",

                    "longitude",

                ]

            )[column]

            .transform(

                lambda s:

                s.rolling(

                    window,

                    min_periods=1,

                ).mean()

            )

        )

    # ======================================================
    # BUILD FEATURES
    # ======================================================

    def build(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Build rolling weather features.
        """

        self.validate(
            dataframe
        )

        dataframe = self.sort(
            dataframe
        )

        #
        # Rainfall
        #

        for window in ROLLING_WINDOWS:

            dataframe[
                f"precipitation_{window}d_sum"
            ] = self.rolling_sum(

                dataframe,

                column="precipitation",

                window=window,

            )

        #
        # Temperature
        #

        for window in ROLLING_WINDOWS:

            dataframe[
                f"temperature_{window}d_mean"
            ] = self.rolling_mean(

                dataframe,

                column="value",

                window=window,

            )

        logger.info(

            "Rolling features created."

        )

        return dataframe