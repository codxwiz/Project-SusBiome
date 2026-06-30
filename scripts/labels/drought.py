"""
============================================================
Drought Label Engineering
============================================================

Creates drought training labels.

============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.labels.models import (

    REQUIRED_COLUMNS,

    DROUGHT_LABEL,

    DROUGHT_DRY_DAYS,

    DROUGHT_RAIN_ANOMALY,

    TEMPERATURE_ANOMALY,

)

logger = logging.getLogger(
    "susbiome.labels.drought"
)


# ==========================================================
# DROUGHT LABEL ENGINEER
# ==========================================================

class DroughtLabelEngineer:
    """
    Generate drought labels.
    """

    def __init__(
        self,
    ) -> None:

        logger.info(
            "Drought Label Engineer initialized."
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
    # BUILD LABEL
    # ======================================================

    @staticmethod
    def build_label(
        dataframe: pd.DataFrame,
    ) -> pd.Series:

        drought = (

            (

                dataframe["consecutive_dry_days"]

                >= DROUGHT_DRY_DAYS

            )

            &

            (

                dataframe["precipitation_anomaly"]

                <= DROUGHT_RAIN_ANOMALY

            )

            &

            (

                dataframe["temperature_anomaly"]

                >= TEMPERATURE_ANOMALY

            )

        )

        return drought.astype("int8")

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

        dataframe[DROUGHT_LABEL] = self.build_label(
            dataframe
        )

        logger.info(
            "Drought labels created."
        )

        return dataframe