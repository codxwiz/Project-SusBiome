"""
============================================================
Feature Engineering Pipeline
============================================================

Combines all feature engineering modules.

Input
-----
Unified Dataset

Output
------
Machine Learning Dataset

============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.features.models import (
    REQUIRED_COLUMNS,
)

from scripts.features.rolling import (
    RollingFeatureEngineer,
)

from scripts.features.climate import (
    ClimateFeatureEngineer,
)

logger = logging.getLogger(
    "susbiome.features.engineering"
)


# ==========================================================
# FEATURE ENGINEERING
# ==========================================================


class FeatureEngineering:
    """
    Main Feature Engineering pipeline.
    """

    def __init__(
        self,
        *,
        require_history: bool = False,
        minimum_history_days: int = 90,
    ) -> None:

        self.rolling = RollingFeatureEngineer()

        self.climate = ClimateFeatureEngineer()

        self.require_history = require_history
        self.minimum_history_days = minimum_history_days

        logger.info(
            "Feature Engineering initialized."
        )

    # ======================================================
# VALIDATE
# ======================================================

    @staticmethod
    def validate(
        dataframe: pd.DataFrame,
    ) -> None:
        """
        Validate input dataset.
        """
        #
        # Empty dataset
        #

        if dataframe.empty:

            raise ValueError(
                "Input dataset is empty."
            )

        #
        # Required columns
        #

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

        #
        # valid_time must be datetime
        #

        if not pd.api.types.is_datetime64_any_dtype(
            dataframe["valid_time"]
        ):

            raise TypeError(
                "valid_time must be datetime."
            )

        #
        # precipitation must be numeric
        #

        if not pd.api.types.is_numeric_dtype(
            dataframe["precipitation"]
        ):

            raise TypeError(
                "precipitation must be numeric."
            )

        #
        # ERA5 value must be numeric
        #

        if not pd.api.types.is_numeric_dtype(
            dataframe["value"]
        ):

            raise TypeError(
                "value must be numeric."
            )

        #
        # Duplicate spatiotemporal observations
        #

        duplicates = dataframe.duplicated(

            subset=[

                "longitude",

                "latitude",

                "valid_time",

            ]

        ).sum()

        if duplicates:

            raise ValueError(

                f"{duplicates} duplicate observations found."

            )

    # ======================================================
    # CALENDAR FEATURES
    # ======================================================

    @staticmethod
    def calendar_features(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:

        dataframe = dataframe.copy()

        time = pd.to_datetime(

            dataframe["valid_time"],

            utc=True,

        )

        dataframe["year"] = time.dt.year

        dataframe["month"] = time.dt.month

        dataframe["day"] = time.dt.day

        dataframe["day_of_year"] = time.dt.dayofyear

        dataframe["week"] = time.dt.isocalendar().week.astype(int)

        dataframe["quarter"] = time.dt.quarter

        dataframe["season"] = (

            ((time.dt.month % 12) // 3) + 1

        )

        return dataframe

    # ======================================================
    # SORT
    # ======================================================

    @staticmethod
    def sort(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:

        return (

            dataframe

            .sort_values(

                [

                    "latitude",

                    "longitude",

                    "valid_time",

                ]

            )

            .reset_index(

                drop=True

            )

        )

    # ======================================================
    # CLEAN
    # ======================================================

    @staticmethod
    def clean(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:

        dataframe = dataframe.copy()

        dataframe = dataframe.drop_duplicates()

        dataframe = dataframe.sort_values(

            [

                "latitude",

                "longitude",

                "valid_time",

            ]

        )

        dataframe = dataframe.reset_index(

            drop=True

        )

        return dataframe

    # ======================================================
    # BUILD
    # ======================================================

    def build(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:

        logger.info(
            "Starting Feature Engineering."
        )

        self.validate(
            dataframe
        )

        dataframe = self.sort(
            dataframe
        )

        history_days = pd.to_datetime(
            dataframe["valid_time"], utc=True
        ).dt.normalize().nunique()

        if self.require_history and history_days < self.minimum_history_days:
            raise ValueError(
                f"Production features require at least "
                f"{self.minimum_history_days} distinct days; found {history_days}."
            )

        if history_days >= 7:

            logger.info("Rolling features...")
            dataframe = self.rolling.build(
                dataframe
            )

            logger.info("Climate features...")
            dataframe = self.climate.build(
                dataframe
            )

        else:

            logger.warning(
                "Insufficient historical data. "
                "Skipping rolling and climate features."
            )

            dataframe["precipitation_7d_sum"] = dataframe["precipitation"]

            dataframe["precipitation_30d_sum"] = dataframe["precipitation"]

            dataframe["precipitation_90d_sum"] = dataframe["precipitation"]

            dataframe["temperature_7d_mean"] = dataframe["value"]

            dataframe["temperature_30d_mean"] = dataframe["value"]

            dataframe["temperature_90d_mean"] = dataframe["value"]

            dataframe["temperature_anomaly"] = 0.0

            dataframe["precipitation_anomaly"] = 0.0

            dataframe["consecutive_dry_days"] = 0

            dataframe["consecutive_wet_days"] = 0

            dataframe["rainfall_intensity"] = (
                dataframe["precipitation"] >= 50.0
            ).astype("int8")

        logger.info("Calendar features...")
        dataframe = self.calendar_features(
            dataframe
        )

        logger.info("Cleaning...")
        dataframe = self.clean(
            dataframe
        )

        self.validate(
            dataframe
        )

        return dataframe
