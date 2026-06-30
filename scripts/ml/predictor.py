"""
============================================================
Machine Learning Predictor
============================================================

Loads trained models and generates predictions.

============================================================
"""

from __future__ import annotations

import logging

from narwhals import dataframe
import pandas as pd

from scripts.ml.flood import FloodModel
from scripts.ml.drought import DroughtModel
from scripts.ml.cyclone import CycloneModel

logger = logging.getLogger(
    "susbiome.ml.predictor"
)


# ==========================================================
# MACHINE LEARNING PREDICTOR
# ==========================================================

class MLPredictor:
    """
    Loads trained models and performs inference.
    """

    def __init__(
        self,
    ) -> None:

        self.flood = FloodModel()

        self.drought = DroughtModel()

        self.cyclone = CycloneModel()

        self.flood.load()

        self.drought.load()

        self.cyclone.load()

        logger.info(
            "ML Predictor initialized."
        )

    # ======================================================
    # FLOOD
    # ======================================================

    def predict_flood(
        self,
        dataframe: pd.DataFrame,
    ):

        return self.flood.predict(
            dataframe
        )

    # ======================================================
    # DROUGHT
    # ======================================================

    def predict_drought(
        self,
        dataframe: pd.DataFrame,
    ):

        return self.drought.predict(
            dataframe
        )

    # ======================================================
    # CYCLONE
    # ======================================================

    def predict_cyclone(
        self,
        dataframe: pd.DataFrame,
    ):

        return self.cyclone.predict(
            dataframe
        )

    # ======================================================
    # ALL PREDICTIONS
    # ======================================================

    def predict(
        self,
        dataframe: pd.DataFrame,
    ):

        #
        # Build ML feature matrix
        #

        X = dataframe.drop(

            columns=[

                "longitude",

                "latitude",

                "valid_time",

                "flood_risk",

                "drought_risk",

                "cyclone_risk",

            ],

            errors="ignore",

        )

        dataframe["flood_prediction"] = (
            self.predict_flood(
                X
            )
        )

        dataframe["drought_prediction"] = (
            self.predict_drought(
                X
            )
        )

        dataframe["cyclone_prediction"] = (
            self.predict_cyclone(
                X
            )
        )

        return dataframe