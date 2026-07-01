"""
==============================================================
Project SusBiome
Dashboard Loader
==============================================================

Loads datasets used by the Dashboard.

Responsibilities
----------------
• Load Prediction dataset
• Load Risk dataset
• Validate datasets
• Report dataset status
• Cache loaded datasets

This module contains NO Streamlit or plotting logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.dashboard.models import (
    ASSESSMENT_DATASET,
    DatasetStatus,
    LOCATIONS_DATASET,
    PREDICTION_DATASET,
    RISK_DATASET,
)

logger = logging.getLogger(__name__)


class DashboardLoader:
    """
    Dashboard dataset loader.
    """

    def __init__(
        self,
    ) -> None:

        self._prediction: pd.DataFrame | None = None

        self._risk: pd.DataFrame | None = None

        self._assessment: pd.DataFrame | None = None

    # ======================================================
    # LOAD DATASET
    # ======================================================

    @staticmethod
    def load(
        path: str | Path,
    ) -> pd.DataFrame:
        """
        Load a dataset.
        """

        path = Path(path)

        if not path.exists():

            raise FileNotFoundError(
                path
            )

        logger.info(
            "Loading %s",
            path,
        )

        if path.suffix == ".parquet":

            dataframe = pd.read_parquet(
                path,
            )

        elif path.suffix == ".csv":

            dataframe = pd.read_csv(
                path,
            )

        else:

            raise ValueError(

                f"Unsupported file type: {path.suffix}"

            )

        DashboardLoader.validate(
            dataframe
        )

        return dataframe

    # ======================================================
    # VALIDATE
    # ======================================================

    @staticmethod
    def validate(
        dataframe: pd.DataFrame,
    ) -> None:
        """
        Validate dashboard dataset.
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
                "Dataset is empty."
            )

    # ======================================================
    # PREDICTION
    # ======================================================

    def prediction(
        self,
    ) -> pd.DataFrame:
        """
        Load prediction dataset.
        """

        if self._prediction is None:

            self._prediction = self.load(
                PREDICTION_DATASET,
            )

        return self._prediction.copy()

    # ======================================================
    # RISK
    # ======================================================

    def risk(
        self,
    ) -> pd.DataFrame:
        """
        Load risk dataset.
        """

        if self._risk is None:

            self._risk = self.load(
                RISK_DATASET,
            )

        return self._risk.copy()

    @staticmethod
    def locations() -> pd.DataFrame:
        """Load the canonical Northeast India district registry."""
        locations = pd.read_csv(LOCATIONS_DATASET)
        required = {"state", "district", "latitude", "longitude"}
        missing = required - set(locations.columns)
        if missing:
            raise ValueError("Location registry is missing: " + ", ".join(sorted(missing)))
        if locations.duplicated(["state", "district"]).any():
            raise ValueError("Location registry contains duplicate districts.")
        return locations.sort_values(["state", "district"]).reset_index(drop=True)

    def assessment(self) -> pd.DataFrame:
        """Load the operational district assessment and forecast contract."""
        if self._assessment is None:
            self._assessment = self.load(ASSESSMENT_DATASET)
        return self._assessment.copy()

    @staticmethod
    def filter_district(dataframe: pd.DataFrame, location: pd.Series) -> pd.DataFrame:
        """Select an explicit district or its nearest representative grid cell."""
        if {"state", "district"}.issubset(dataframe.columns):
            filtered = dataframe.loc[
                dataframe["state"].eq(location["state"])
                & dataframe["district"].eq(location["district"])
            ]
            if not filtered.empty:
                return filtered.copy()

        latitude = pd.to_numeric(dataframe["latitude"], errors="coerce")
        longitude = pd.to_numeric(dataframe["longitude"], errors="coerce")
        latitude_scale = np.cos(np.radians(float(location["latitude"])))
        distance = (
            (latitude - float(location["latitude"])) ** 2
            + ((longitude - float(location["longitude"])) * latitude_scale) ** 2
        )
        nearest = distance.idxmin()
        selected_latitude = latitude.loc[nearest]
        selected_longitude = longitude.loc[nearest]
        return dataframe.loc[
            np.isclose(latitude, selected_latitude)
            & np.isclose(longitude, selected_longitude)
        ].copy()

    # ======================================================
    # RELOAD
    # ======================================================

    def reload(
        self,
    ) -> None:
        """
        Clear cached datasets.
        """

        self._prediction = None

        self._risk = None

        self._assessment = None

        logger.info(
            "Dashboard cache cleared."
        )

    # ======================================================
    # STATUS
    # ======================================================

    @staticmethod
    def status(
    ) -> DatasetStatus:
        """
        Dataset availability.
        """

        return DatasetStatus(

            prediction=PREDICTION_DATASET.exists(),

            risk=RISK_DATASET.exists(),

            assessment=ASSESSMENT_DATASET.exists(),

        )

    # ======================================================
    # READY
    # ======================================================

    @classmethod
    def ready(
        cls,
    ) -> bool:
        """
        Dashboard readiness.
        """

        status = cls.status()

        return (

            status.assessment or (status.prediction and status.risk)

        )

    # ======================================================
    # SUMMARY
    # ======================================================

    def summary(
        self,
    ) -> dict:
        """
        Dataset summary.
        """

        prediction = self.prediction()

        risk = self.risk()

        return {

            "prediction_rows": len(
                prediction,
            ),

            "risk_rows": len(
                risk,
            ),

            "prediction_columns": len(
                prediction.columns,
            ),

            "risk_columns": len(
                risk.columns,
            ),

            "prediction_dataset": str(
                PREDICTION_DATASET,
            ),

            "risk_dataset": str(
                RISK_DATASET,
            ),

        }

    # ======================================================
    # LOAD ALL
    # ======================================================

    def load_all(
        self,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load all dashboard datasets.
        """

        prediction = self.prediction()

        risk = self.risk()

        logger.info(
            "Dashboard datasets loaded."
        )

        return (

            prediction,

            risk,

        )
