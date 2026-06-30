"""
==============================================================
Project SusBiome
Prediction Inference Engine
==============================================================

Runs inference using trained Machine Learning models.

Responsibilities
----------------
• Validate prediction dataset
• Load trained models
• Run Flood inference
• Run Drought inference
• Run Cyclone inference
• Return prediction dataframe

This module performs NO formatting and NO file I/O.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.prediction.loader import PredictionLoader
from scripts.prediction.models import (
    FEATURE_COLUMNS,
    PREDICTION_COLUMNS,
    REQUIRED_COLUMNS,
)

logger = logging.getLogger(__name__)


class PredictionInference:
    """
    Prediction inference engine.
    """

    def __init__(
        self,
        loader: PredictionLoader | None = None,
    ) -> None:

        self.loader = loader or PredictionLoader()

        self.models = self.loader.load_all()

        logger.info(
            "Prediction Inference initialized."
        )

    # ======================================================
    @staticmethod
    def classify(model, X: pd.DataFrame):
        """Apply the validation-selected decision threshold."""
        classes = list(getattr(model, "classes_", []))
        if not hasattr(model, "predict_proba") or 1 not in classes:
            return model.predict(X)
        probability = model.predict_proba(X)[:, classes.index(1)]
        threshold = float(getattr(model, "susbiome_threshold_", 0.5))
        return (probability >= threshold).astype("int8")

    # ======================================================
    # VALIDATE
    # ======================================================

    @staticmethod
    def validate(
        dataframe: pd.DataFrame,
    ) -> None:
        """
        Validate inference dataset.
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
                "Input dataset is empty."
            )

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
    # FEATURES
    # ======================================================

    @staticmethod
    def features(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Build feature matrix.
        """

        return dataframe.loc[
            :,
            FEATURE_COLUMNS,
        ].copy()

    # ======================================================
    # FLOOD
    # ======================================================

    def predict_flood(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.Series:

        X = self.features(
            dataframe,
        )

        model = self.models["flood"]

        return pd.Series(

            self.classify(model,
                X,
            ),

            index=dataframe.index,

            name="flood_prediction",

        )

    # ======================================================
    # DROUGHT
    # ======================================================

    def predict_drought(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.Series:

        X = self.features(
            dataframe,
        )

        model = self.models.get("drought")
        if model is None:
            return pd.Series(0, index=dataframe.index, name="drought_prediction")

        return pd.Series(

            self.classify(model,
                X,
            ),

            index=dataframe.index,

            name="drought_prediction",

        )

    # ======================================================
    # CYCLONE
    # ======================================================

    def predict_cyclone(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.Series:

        X = self.features(
            dataframe,
        )

        model = self.models["cyclone"]

        return pd.Series(

            self.classify(model,
                X,
            ),

            index=dataframe.index,

            name="cyclone_prediction",

        )

    # ======================================================
    # PROBABILITY
    # ======================================================

    @staticmethod
    def probability(
        model,
        X: pd.DataFrame,
        index: pd.Index,
        column: str,
    ) -> pd.Series:
        """
        Return positive-class probability.

        If the estimator does not support predict_proba,
        return zeros.
        """

        if not hasattr(
            model,
            "predict_proba",
        ):

            return pd.Series(

                0.0,

                index=index,

                name=column,

            )

        probability = model.predict_proba(
            X,
        )

        classes = list(getattr(model, "classes_", []))
        if 1 not in classes:
            values = [0.0] * len(index)
        else:
            values = probability[:, classes.index(1)]

        return pd.Series(

            values,

            index=index,

            name=column,

        )

    # ======================================================
    # PREDICT
    # ======================================================

    def predict(
        self,
        dataframe: pd.DataFrame,
        *,
        include_probability: bool = True,
    ) -> pd.DataFrame:
        """
        Run inference.
        """

        self.validate(
            dataframe,
        )

        logger.info(
            "Running prediction inference."
        )

        result = dataframe.copy()

        X = self.features(
            result,
        )

        flood_model = self.models["flood"]

        drought_model = self.models.get("drought")

        cyclone_model = self.models["cyclone"]

        #
        # Predictions
        #

        result["flood_prediction"] = (

            self.classify(flood_model,
                X,
            )

        )

        result["drought_available"] = drought_model is not None
        result["drought_prediction"] = (
            self.classify(drought_model, X) if drought_model is not None else 0
        )

        result["cyclone_prediction"] = (

            self.classify(cyclone_model,
                X,
            )

        )

        #
        # Probabilities
        #

        if include_probability:

            result["flood_probability"] = (

                self.probability(

                    flood_model,

                    X,

                    result.index,

                    "flood_probability",

                )

            )

            result["drought_probability"] = (
                self.probability(
                    drought_model, X, result.index, "drought_probability"
                )
                if drought_model is not None
                else float("nan")
            )

            result["cyclone_probability"] = (

                self.probability(

                    cyclone_model,

                    X,

                    result.index,

                    "cyclone_probability",

                )

            )

        logger.info(
            "Inference complete."
        )

        return result

    # ======================================================
    # AVAILABLE
    # ======================================================

    @staticmethod
    def prediction_columns() -> list[str]:
        """
        Prediction column names.
        """

        return PREDICTION_COLUMNS.copy()
