"""
==============================================================
Project SusBiome
Dashboard Tables
==============================================================

Interactive dashboard tables.

Responsibilities
----------------
• Latest Predictions
• Highest Risk Locations
• Flood Table
• Drought Table
• Cyclone Table
• Search & Filter Helpers

This module contains NO Streamlit layout logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging

import pandas as pd

from scripts.dashboard.models import (
    TABLE_COLUMNS,
)

logger = logging.getLogger(__name__)


class DashboardTables:
    """
    Dashboard table builder.
    """

    # ======================================================
    # VALIDATE
    # ======================================================

    @staticmethod
    def validate(
        dataframe: pd.DataFrame,
    ) -> None:
        """
        Validate dataset.
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
    # DISPLAY COLUMNS
    # ======================================================

    @staticmethod
    def columns(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Keep dashboard columns.
        """

        DashboardTables.validate(
            dataframe,
        )

        columns = [

            column

            for column in TABLE_COLUMNS

            if column in dataframe.columns

        ]

        return dataframe.loc[
            :,
            columns,
        ]

    # ======================================================
    # LATEST
    # ======================================================

    def latest(
        self,
        dataframe: pd.DataFrame,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Latest observations.
        """

        dataframe = self.columns(
            dataframe,
        )

        dataframe = dataframe.sort_values(

            by="valid_time",

            ascending=False,

        )

        return dataframe.head(
            limit,
        )

    # ======================================================
    # HIGHEST RISK
    # ======================================================

    def highest_risk(
        self,
        dataframe: pd.DataFrame,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Highest overall risk.
        """

        DashboardTables.validate(
            dataframe,
        )

        dataframe = dataframe.sort_values(

            by=[

                "overall_risk_score",

                "overall_risk_level",

            ],

            ascending=False,

        )

        return self.columns(

            dataframe.head(
                limit,
            )

        )

    # ======================================================
    # FLOOD
    # ======================================================

    def flood(
        self,
        dataframe: pd.DataFrame,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Flood observations.
        """

        DashboardTables.validate(
            dataframe,
        )

        dataframe = dataframe[

            dataframe[
                "flood_prediction"
            ] == 1

        ]

        dataframe = dataframe.sort_values(

            by="flood_probability",

            ascending=False,

        )

        return self.columns(

            dataframe.head(
                limit,
            )

        )

    # ======================================================
    # DROUGHT
    # ======================================================

    def drought(
        self,
        dataframe: pd.DataFrame,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Drought observations.
        """

        DashboardTables.validate(
            dataframe,
        )

        dataframe = dataframe[

            dataframe[
                "drought_prediction"
            ] == 1

        ]

        dataframe = dataframe.sort_values(

            by="drought_probability",

            ascending=False,

        )

        return self.columns(

            dataframe.head(
                limit,
            )

        )

    # ======================================================
    # CYCLONE
    # ======================================================

    def cyclone(
        self,
        dataframe: pd.DataFrame,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Cyclone observations.
        """

        DashboardTables.validate(
            dataframe,
        )

        dataframe = dataframe[

            dataframe[
                "cyclone_prediction"
            ] == 1

        ]

        dataframe = dataframe.sort_values(

            by="cyclone_probability",

            ascending=False,

        )

        return self.columns(

            dataframe.head(
                limit,
            )

        )

    # ======================================================
    # SEARCH
    # ======================================================

    @staticmethod
    def search(
        dataframe: pd.DataFrame,
        text: str,
    ) -> pd.DataFrame:
        """
        Search dataset.
        """

        DashboardTables.validate(
            dataframe,
        )

        if not text:

            return dataframe

        mask = (

            dataframe

            .astype(str)

            .apply(

                lambda column:

                column.str.contains(

                    text,

                    case=False,

                    na=False,

                )

            )

            .any(axis=1)

        )

        return dataframe.loc[
            mask
        ]

    # ======================================================
    # FILTER
    # ======================================================

    @staticmethod
    def filter_level(
        dataframe: pd.DataFrame,
        level: str,
    ) -> pd.DataFrame:
        """
        Filter overall risk level.
        """

        DashboardTables.validate(
            dataframe,
        )

        return dataframe[

            dataframe[
                "overall_risk_level"
            ] == level

        ]

    # ======================================================
    # SUMMARY
    # ======================================================

    @staticmethod
    def summary(
        dataframe: pd.DataFrame,
    ) -> dict:
        """
        Table summary.
        """

        DashboardTables.validate(
            dataframe,
        )

        return {

            "rows": len(
                dataframe,
            ),

            "columns": len(
                dataframe.columns,
            ),

            "highest_risk": (

                dataframe[
                    "overall_risk_level"
                ]

                .value_counts()

                .idxmax()

            ),

        }