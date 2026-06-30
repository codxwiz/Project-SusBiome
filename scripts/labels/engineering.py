"""
============================================================
Label Engineering
============================================================

Coordinates all label generation.

Pipeline

Flood Labels
        ↓
Drought Labels
        ↓
Cyclone Labels

============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.labels.flood import FloodLabelEngineer
from scripts.labels.drought import DroughtLabelEngineer
from scripts.labels.cyclone import CycloneLabelEngineer

logger = logging.getLogger(
    "susbiome.labels.engineering"
)


# ==========================================================
# LABEL ENGINEERING
# ==========================================================

class LabelEngineering:
    """
    Runs all label generators.
    """

    def __init__(
        self,
    ) -> None:

        self.flood = FloodLabelEngineer()

        self.drought = DroughtLabelEngineer()

        self.cyclone = CycloneLabelEngineer()

        logger.info(
            "Label Engineering initialized."
        )

    # ======================================================
    # BUILD
    # ======================================================

    def build(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Build all training labels.
        """

        logger.info(
            "Starting label engineering."
        )

        #
        # Flood
        #

        dataframe = self.flood.build(
            dataframe
        )

        #
        # Drought
        #

        dataframe = self.drought.build(
            dataframe
        )

        #
        # Cyclone
        #

        dataframe = self.cyclone.build(
            dataframe
        )

        # These labels are useful for exploratory baselines only. Production
        # training must replace them through verified event alignment.
        dataframe["label_method"] = "weather_threshold_proxy"

        logger.info(
            "Label engineering completed."
        )

        return dataframe
