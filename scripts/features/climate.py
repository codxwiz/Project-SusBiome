"""
============================================================
Climate Feature Engineering
============================================================

Computes climate-derived indicators.

Input
-----
DataFrame

Output
------
DataFrame with climate features.

============================================================
"""

from __future__ import annotations

import logging
import pandas as pd

from scripts.features.models import (
    REQUIRED_COLUMNS,
    DRY_DAY_THRESHOLD,
    HEAVY_RAIN_THRESHOLD,
    HOT_DAY_THRESHOLD,
    COLD_DAY_THRESHOLD,
)

logger = logging.getLogger(
    "susbiome.features.climate"
)


# ==========================================================
# CLIMATE FEATURE ENGINEER
# ==========================================================

class ClimateFeatureEngineer:
    """
    Climate feature engineering.
    """

    def __init__(self) -> None:

        logger.info(
            "Climate Feature Engineer initialized."
        )

    # ======================================================
    # VALIDATE
    # ======================================================

    @staticmethod
    def validate(
        dataframe: pd.DataFrame,
    ) -> None:

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
    # TEMPERATURE ANOMALY
    # ======================================================

    @staticmethod
    def temperature_anomaly(
        dataframe: pd.DataFrame,
    ) -> pd.Series:

        month = pd.to_datetime(dataframe["valid_time"], utc=True).dt.month
        climatology = dataframe.assign(_month=month).groupby(
            ["latitude", "longitude", "_month"]
        )["value"].transform("mean")

        return (

            dataframe["value"]

            - climatology

        )

    # ======================================================
    # PRECIPITATION ANOMALY
    # ======================================================

    @staticmethod
    def precipitation_anomaly(
        dataframe: pd.DataFrame,
    ) -> pd.Series:

        month = pd.to_datetime(dataframe["valid_time"], utc=True).dt.month
        climatology = dataframe.assign(_month=month).groupby(
            ["latitude", "longitude", "_month"]
        )["precipitation"].transform("mean")

        return (

            dataframe["precipitation"]

            - climatology

        )

    # ======================================================
    # CONSECUTIVE DRY DAYS
    # ======================================================

    @staticmethod
    def consecutive_dry_days(
        dataframe: pd.DataFrame,
    ) -> pd.Series:
        """
        Compute consecutive dry-day streaks.
        """

        result = pd.Series(
            0,
            index=dataframe.index,
            dtype="int32",
        )

        for _, group in dataframe.groupby(
            [
             "latitude",
                "longitude",
            ],
            sort=False,
        ):

            streak = 0

            values = []

            for rain in group["precipitation"]:

                if rain < DRY_DAY_THRESHOLD:

                    streak += 1

                else:

                    streak = 0

                values.append(streak)

            result.loc[group.index] = values

        return result

    # ======================================================
    # CONSECUTIVE WET DAYS
    # ======================================================

    @staticmethod
    def consecutive_wet_days(
        dataframe: pd.DataFrame,
    ) -> pd.Series:
        """
        Compute consecutive wet-day streaks.
        """

        result = pd.Series(
            0,
            index=dataframe.index,
            dtype="int32",
        )

        for _, group in dataframe.groupby(
            [
                "latitude",
                "longitude",
            ],
            sort=False,
        ):

            streak = 0

            values = []

            for rain in group["precipitation"]:

                if rain >= DRY_DAY_THRESHOLD:

                    streak += 1

                else:

                    streak = 0

                values.append(streak)

            result.loc[group.index] = values

        return result

    # ======================================================
    # RAINFALL INTENSITY
    # ======================================================

    @staticmethod
    def rainfall_intensity(
        dataframe: pd.DataFrame,
    ) -> pd.Series:

        return (

            dataframe["precipitation"]

            >= HEAVY_RAIN_THRESHOLD

        ).astype(int)

    # ======================================================
    # HOT DAY
    # ======================================================

    @staticmethod
    def hot_day(
        dataframe: pd.DataFrame,
    ) -> pd.Series:

        return (

            dataframe["value"]

            >= HOT_DAY_THRESHOLD

        ).astype(int)

    # ======================================================
    # COLD DAY
    # ======================================================

    @staticmethod
    def cold_day(
        dataframe: pd.DataFrame,
    ) -> pd.Series:

        return (

            dataframe["value"]

            <= COLD_DAY_THRESHOLD

        ).astype(int)

    # ======================================================
    # BUILD
    # ======================================================

    def build(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:

        self.validate(
            dataframe
        )

        dataframe = dataframe.copy()

        dataframe[
            "temperature_anomaly"
        ] = self.temperature_anomaly(
            dataframe
        )

        dataframe[
            "precipitation_anomaly"
        ] = self.precipitation_anomaly(
            dataframe
        )

        dataframe[
            "consecutive_dry_days"
        ] = self.consecutive_dry_days(
            dataframe
        )

        dataframe[
            "consecutive_wet_days"
        ] = self.consecutive_wet_days(
            dataframe
        )

        dataframe[
            "rainfall_intensity"
        ] = self.rainfall_intensity(
            dataframe
        )

        dataframe[
            "hot_day"
        ] = self.hot_day(
            dataframe
        )

        dataframe[
            "cold_day"
        ] = self.cold_day(
            dataframe
        )

        logger.info(
            "Climate features created."
        )

        return dataframe
