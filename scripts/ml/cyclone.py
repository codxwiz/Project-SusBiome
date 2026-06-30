"""
============================================================
Cyclone Prediction Model
============================================================

Machine Learning model for cyclone prediction.

============================================================
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

from scripts.ml.models import (
    CYCLONE_MODEL,
    RF_N_ESTIMATORS,
    RF_MAX_DEPTH,
    RF_MIN_SAMPLES_SPLIT,
    RF_MIN_SAMPLES_LEAF,
    RF_N_JOBS,
    RANDOM_STATE,
)

logger = logging.getLogger(
    "susbiome.ml.cyclone"
)


# ==========================================================
# CYCLONE MODEL
# ==========================================================

class CycloneModel:
    """
    Cyclone prediction model.
    """

    def __init__(
        self,
    ) -> None:

        self.model = RandomForestClassifier(

            n_estimators=RF_N_ESTIMATORS,

            max_depth=RF_MAX_DEPTH,

            min_samples_split=RF_MIN_SAMPLES_SPLIT,

            min_samples_leaf=RF_MIN_SAMPLES_LEAF,

            random_state=RANDOM_STATE,

            n_jobs=RF_N_JOBS,

            class_weight="balanced_subsample",

        )

        logger.info(
            "Cyclone model initialized."
        )

    # ======================================================
    # TRAIN
    # ======================================================

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
    ) -> None:

        logger.info(
            "Training Cyclone model."
        )

        self.model.fit(

            X_train,

            y_train,

        )

    # ======================================================
    # PREDICT
    # ======================================================

    def predict(
        self,
        X: pd.DataFrame,
    ):

        return self.model.predict(
            X
        )

    # ======================================================
    # EVALUATE
    # ======================================================

    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> dict:

        prediction = self.predict(
            X_test
        )

        return {

            "accuracy": accuracy_score(
                y_test,
                prediction,
            ),

            "precision": precision_score(
                y_test,
                prediction,
                zero_division=0,
            ),

            "recall": recall_score(
                y_test,
                prediction,
                zero_division=0,
            ),

            "f1": f1_score(
                y_test,
                prediction,
                zero_division=0,
            ),

        }

    # ======================================================
    # SAVE
    # ======================================================

    def save(
        self,
        path: Path = CYCLONE_MODEL,
    ) -> None:

        path.parent.mkdir(

            parents=True,

            exist_ok=True,

        )

        joblib.dump(

            self.model,

            path,

        )

        logger.info(

            "Saved Cyclone model: %s",

            path,

        )

    # ======================================================
    # LOAD
    # ======================================================

    def load(
        self,
        path: Path = CYCLONE_MODEL,
    ) -> None:

        self.model = joblib.load(
            path
        )

        logger.info(

            "Loaded Cyclone model: %s",

            path,

        )
