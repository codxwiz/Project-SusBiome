"""
==============================================================
Project SusBiome
Dashboard Charts
==============================================================

Interactive dashboard charts.

Responsibilities
----------------
• Overall Risk Distribution
• Hazard Distribution
• Prediction Distribution
• Timeline
• KPI Summary Charts

This module contains NO Streamlit layout logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import pandas as pd

try:
    import plotly.express as px  # type: ignore[import]
except ImportError:  # pragma: no cover - fallback for restricted environments
    px = None

if TYPE_CHECKING:
    from plotly.graph_objects import Figure  # type: ignore[import]
else:
    Figure = Any

from scripts.dashboard.models import (
    CHART_HEIGHT,
    CHART_WIDTH,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DashboardCharts:
    """
    Dashboard chart builder.
    """

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
    # BAR
    # ======================================================

    @staticmethod
    def _bar(
        dataframe: pd.DataFrame,
        column: str,
        title: str,
    ) -> Figure:
        """
        Generic bar chart.
        """

        DashboardCharts.validate(
            dataframe,
        )

        counts = (

            dataframe[column]

            .value_counts()

            .reset_index()

        )

        counts.columns = [

            column,

            "count",

        ]

        figure = px.bar(

            counts,

            x=column,

            y="count",

            title=title,

            text="count",

            height=CHART_HEIGHT,

            width=CHART_WIDTH,

        )

        figure.update_layout(

            xaxis_title="",

            yaxis_title="Count",

        )

        return figure

    # ======================================================
    # PIE
    # ======================================================

    @staticmethod
    def _pie(
        dataframe: pd.DataFrame,
        column: str,
        title: str,
    ) -> Figure:
        """
        Generic pie chart.
        """

        DashboardCharts.validate(
            dataframe,
        )

        counts = (

            dataframe[column]

            .value_counts()

            .reset_index()

        )

        counts.columns = [

            column,

            "count",

        ]

        figure = px.pie(

            counts,

            names=column,

            values="count",

            title=title,

            height=CHART_HEIGHT,

            width=CHART_WIDTH,

        )

        return figure

    # ======================================================
    # OVERALL RISK
    # ======================================================

    def overall_risk(
        self,
        dataframe: pd.DataFrame,
    ) -> Figure:
        """
        Overall Risk Distribution.
        """

        return self._bar(

            dataframe,

            "overall_risk_level",

            "Overall Risk Distribution",

        )

    # ======================================================
    # FLOOD
    # ======================================================

    def flood(
        self,
        dataframe: pd.DataFrame,
    ) -> Figure:
        """
        Flood Risk Distribution.
        """

        return self._bar(

            dataframe,

            "flood_risk_level",

            "Flood Risk Distribution",

        )

    # ======================================================
    # DROUGHT
    # ======================================================

    def drought(
        self,
        dataframe: pd.DataFrame,
    ) -> Figure:
        """
        Drought Risk Distribution.
        """

        return self._bar(

            dataframe,

            "drought_risk_level",

            "Drought Risk Distribution",

        )

    # ======================================================
    # CYCLONE
    # ======================================================

    def cyclone(
        self,
        dataframe: pd.DataFrame,
    ) -> Figure:
        """
        Cyclone Risk Distribution.
        """

        return self._bar(

            dataframe,

            "cyclone_risk_level",

            "Cyclone Risk Distribution",

        )

    # ======================================================
    # DOMINANT HAZARD
    # ======================================================

    def hazards(
        self,
        dataframe: pd.DataFrame,
    ) -> Figure:
        """
        Dominant Hazard Distribution.
        """

        return self._pie(

            dataframe,

            "dominant_hazard",

            "Dominant Hazard Distribution",

        )

    # ======================================================
    # TIMELINE
    # ======================================================

    def timeline(
        self,
        dataframe: pd.DataFrame,
    ) -> Figure:
        """
        Timeline of overall risk.
        """

        DashboardCharts.validate(
            dataframe,
        )

        timeline = (

            dataframe

            .groupby(

                "valid_time",

                as_index=False,

            )["overall_risk_score"]

            .mean()

        )

        figure = px.line(

            timeline,

            x="valid_time",

            y="overall_risk_score",

            title="Average Overall Risk",

            height=CHART_HEIGHT,

            width=CHART_WIDTH,

        )

        figure.update_layout(

            xaxis_title="Time",

            yaxis_title="Average Risk Score",

        )

        return figure

    # ======================================================
    # KPI
    # ======================================================

    @staticmethod
    def kpis(
        dataframe: pd.DataFrame,
    ) -> dict:
        """
        Dashboard KPI summary.
        """

        DashboardCharts.validate(
            dataframe,
        )

        return {

            "rows": len(
                dataframe,
            ),

            "highest_risk": int(

                dataframe[
                    "overall_risk_score"
                ].max()

            ),

            "average_risk": round(

                dataframe[
                    "overall_risk_score"
                ].mean(),

                2,

            ),

            "dominant_hazard": (

                dataframe[
                    "dominant_hazard"
                ]

                .mode()

                .iloc[0]

            ),

        }