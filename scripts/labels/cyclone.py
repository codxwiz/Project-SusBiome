"""
============================================================
Cyclone Label Engineering
============================================================

Creates cyclone training labels.

============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.labels.models import (

    REQUIRED_COLUMNS,

    CYCLONE_LABEL,

    CYCLONE_RAIN,

    CYCLONE_TEMPERATURE,

)

logger = logging.getLogger(
    "susbiome.labels.cyclone"
)


# ==========================================================
# CYCLONE LABEL ENGINEER
# ==========================================================

class CycloneLabelEngineer:
    """
    Generate cyclone labels.
    """

    def __init__(
        self,
    ) -> None:

        logger.info(
            "Cyclone Label Engineer initialized."
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

        cyclone = (

            (

                dataframe["precipitation"]

                >= CYCLONE_RAIN

            )

            &

            (

                dataframe["value"]

                >= CYCLONE_TEMPERATURE

            )

        )

        return cyclone.astype("int8")

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

        dataframe[CYCLONE_LABEL] = self.build_label(
            dataframe
        )

        logger.info(
            "Cyclone labels created."
        )

        return dataframe