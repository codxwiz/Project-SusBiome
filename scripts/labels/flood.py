"""
============================================================
Flood Label Engineering
============================================================

Creates flood training labels.

============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.labels.models import (

    REQUIRED_COLUMNS,

    FLOOD_LABEL,

    FLOOD_RAIN_1DAY,

    FLOOD_RAIN_7DAY,

    FLOOD_WET_DAYS,

)

logger = logging.getLogger(
    "susbiome.labels.flood"
)


# ==========================================================
# FLOOD LABEL ENGINEER
# ==========================================================

class FloodLabelEngineer:
    """
    Generate flood labels.
    """

    def __init__(
        self,
    ) -> None:

        logger.info(
            "Flood Label Engineer initialized."
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

        flood = (

            (
                dataframe["precipitation"]

                >= FLOOD_RAIN_1DAY

            )

            |

            (
                dataframe["precipitation_7d_sum"]

                >= FLOOD_RAIN_7DAY

            )

            |

            (
                dataframe["consecutive_wet_days"]

                >= FLOOD_WET_DAYS

            )

        )

        return flood.astype("int8")

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

        dataframe[FLOOD_LABEL] = self.build_label(
            dataframe
        )

        logger.info(
            "Flood labels created."
        )

        return dataframe