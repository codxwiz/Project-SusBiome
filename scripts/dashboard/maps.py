"""
==============================================================
Project SusBiome
Dashboard Maps
==============================================================

Interactive map generation for the Dashboard.

Responsibilities
----------------
• Overall Risk Map
• Flood Risk Map
• Drought Risk Map
• Cyclone Risk Map

This module contains NO Streamlit layout logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging

import pandas as pd
# pyright: reportMissingImports=false
import plotly.express as px
from plotly.graph_objects import Figure

from scripts.dashboard.models import (
    CHART_HEIGHT,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_ZOOM,
    RISK_COLORS,
)

logger = logging.getLogger(__name__)


class DashboardMaps:
    """
    Interactive dashboard maps.
    """

    # ======================================================
    # VALIDATE
    # ======================================================

    @staticmethod
    def validate(
        dataframe: pd.DataFrame,
    ) -> None:
        """
        Validate map dataset.
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

        required = [

            "latitude",

            "longitude",

            "overall_risk_level",

        ]

        missing = [

            column

            for column in required

            if column not in dataframe.columns

        ]

        if missing:

            raise ValueError(

                "Missing columns: "

                + ", ".join(missing)

            )

    # ======================================================
    # MAP
    # ======================================================

    @staticmethod
    def build(
        dataframe: pd.DataFrame,
        color_column: str,
        title: str,
    ) -> Figure:
        """
        Generic risk map.
        """

        DashboardMaps.validate(
            dataframe,
        )

        logger.info(
            "Creating %s",
            title,
        )

        center = {
            "lat": float(dataframe["latitude"].mean()),
            "lon": float(dataframe["longitude"].mean()),
        }
        figure = px.scatter_map(

            dataframe,

            lat="latitude",

            lon="longitude",

            color=color_column,

            color_discrete_map=RISK_COLORS,

            hover_data=[

                "valid_time",

            ],

            zoom=7 if dataframe[["latitude", "longitude"]].drop_duplicates().shape[0] <= 4 else DEFAULT_ZOOM,

            center=center,

            height=CHART_HEIGHT,

            title=title,

        )

        figure.update_layout(

            margin=dict(

                l=10,

                r=10,

                t=50,

                b=10,

            ),

            legend_title="Risk",

        )

        return figure

    # ======================================================
    # OVERALL
    # ======================================================

    def overall(
        self,
        dataframe: pd.DataFrame,
    ) -> Figure:
        """
        Overall Risk Map.
        """

        return self.build(

            dataframe,

            "overall_risk_level",

            "Overall Risk",

        )

    # ======================================================
    # FLOOD
    # ======================================================

    def flood(
        self,
        dataframe: pd.DataFrame,
    ) -> Figure:
        """
        Flood Risk Map.
        """

        return self.build(

            dataframe,

            "flood_risk_level",

            "Flood Risk",

        )

    # ======================================================
    # DROUGHT
    # ======================================================

    def drought(
        self,
        dataframe: pd.DataFrame,
    ) -> Figure:
        """
        Drought Risk Map.
        """

        return self.build(

            dataframe,

            "drought_risk_level",

            "Drought Risk",

        )

    # ======================================================
    # CYCLONE
    # ======================================================

    def cyclone(
        self,
        dataframe: pd.DataFrame,
    ) -> Figure:
        """
        Cyclone Risk Map.
        """

        return self.build(

            dataframe,

            "cyclone_risk_level",

            "Cyclone Risk",

        )
