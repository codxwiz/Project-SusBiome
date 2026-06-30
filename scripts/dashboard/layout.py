"""
==============================================================
Project SusBiome
Dashboard Layout
==============================================================

Builds the Streamlit dashboard layout.

Responsibilities
----------------
• Page configuration
• Header
• KPI metrics
• Interactive maps
• Charts
• Tables
• Sidebar
• Footer

This module contains NO business logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import pandas as pd
import streamlit as st  # type: ignore

from scripts.dashboard.charts import (
    DashboardCharts,
)

from scripts.dashboard.loader import (
    DashboardLoader,
)

from scripts.dashboard.maps import (
    DashboardMaps,
)

from scripts.dashboard.models import (
    DASHBOARD_NAME,
    DASHBOARD_VERSION,
    LAYOUT,
    PAGE_ICON,
    PAGE_TITLE,
    SIDEBAR_STATE,
)

from scripts.dashboard.tables import (
    DashboardTables,
)


class DashboardLayout:
    """
    Dashboard layout.
    """

    def __init__(
        self,
    ) -> None:

        self.loader = DashboardLoader()

        self.maps = DashboardMaps()

        self.charts = DashboardCharts()

        self.tables = DashboardTables()

    # ======================================================
    # PAGE
    # ======================================================

    @staticmethod
    def page() -> None:
        """
        Configure Streamlit page.
        """

        st.set_page_config(

            page_title=PAGE_TITLE,

            page_icon=PAGE_ICON,

            layout=LAYOUT,

            initial_sidebar_state=SIDEBAR_STATE,

        )

    # ======================================================
    # HEADER
    # ======================================================

    @staticmethod
    def header() -> None:
        """
        Dashboard header.
        """

        st.title(
            PAGE_TITLE,
        )

        st.caption(

            f"{DASHBOARD_NAME} "

            f"v{DASHBOARD_VERSION}"

        )

        st.divider()

    # ======================================================
    # SIDEBAR
    # ======================================================

    @staticmethod
    def sidebar() -> None:
        """
        Sidebar.
        """

        st.sidebar.title(
            "Navigation"
        )

    def district_selection(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
        locations = self.loader.locations()
        states = locations["state"].drop_duplicates().tolist()
        state = st.sidebar.selectbox("State", states)
        districts = locations.loc[locations["state"].eq(state), "district"].tolist()
        district = st.sidebar.selectbox("District", districts)
        location = locations.loc[
            locations["state"].eq(state) & locations["district"].eq(district)
        ].iloc[0]
        return self.loader.filter_district(dataframe, location), state, district

        st.sidebar.success(
            "Dashboard Ready"
        )

        st.sidebar.markdown(
            """
### Sections

• KPI Summary

• Risk Maps

• Charts

• Tables
"""
        )

    # ======================================================
    # KPI
    # ======================================================

    def kpis(
        self,
        dataframe,
    ) -> None:
        """
        KPI cards.
        """

        kpi = self.charts.kpis(
            dataframe,
        )

        col1, col2, col3, col4 = st.columns(
            4,
        )

        col1.metric(
            "Rows",
            kpi["rows"],
        )

        col2.metric(
            "Highest Risk",
            kpi["highest_risk"],
        )

        col3.metric(
            "Average Risk",
            kpi["average_risk"],
        )

        col4.metric(
            "Dominant Hazard",
            kpi["dominant_hazard"],
        )

    # ======================================================
    # MAPS
    # ======================================================

    def maps_section(
        self,
        dataframe,
    ) -> None:
        """
        Interactive maps.
        """

        st.subheader(
            "Risk Maps"
        )

        st.plotly_chart(

            self.maps.overall(
                dataframe,
            ),

            use_container_width=True,

        )

        col1, col2 = st.columns(
            2,
        )

        with col1:

            st.plotly_chart(

                self.maps.flood(
                    dataframe,
                ),

                use_container_width=True,

            )

            st.plotly_chart(

                self.maps.drought(
                    dataframe,
                ),

                use_container_width=True,

            )

        with col2:

            st.plotly_chart(

                self.maps.cyclone(
                    dataframe,
                ),

                use_container_width=True,

            )

    # ======================================================
    # CHARTS
    # ======================================================

    def charts_section(
        self,
        dataframe,
    ) -> None:
        """
        Charts.
        """

        st.subheader(
            "Analytics"
        )

        col1, col2 = st.columns(
            2,
        )

        with col1:

            st.plotly_chart(

                self.charts.overall_risk(
                    dataframe,
                ),

                use_container_width=True,

            )

            st.plotly_chart(

                self.charts.flood(
                    dataframe,
                ),

                use_container_width=True,

            )

        with col2:

            st.plotly_chart(

                self.charts.hazards(
                    dataframe,
                ),

                use_container_width=True,

            )

            st.plotly_chart(

                self.charts.timeline(
                    dataframe,
                ),

                use_container_width=True,

            )

    # ======================================================
    # TABLES
    # ======================================================

    def tables_section(
        self,
        dataframe,
    ) -> None:
        """
        Interactive tables.
        """

        st.subheader(
            "Highest Risk Locations"
        )

        st.dataframe(

            self.tables.highest_risk(
                dataframe,
            ),

            use_container_width=True,

        )

    # ======================================================
    # FOOTER
    # ======================================================

    @staticmethod
    def footer() -> None:
        """
        Footer.
        """

        st.divider()

        st.caption(

            "Project SusBiome "

            "Flood • Drought • Cyclone "

            "Prediction Platform"

        )

    # ======================================================
    # BUILD
    # ======================================================

    def build(
        self,
    ) -> None:
        """
        Build complete dashboard.
        """

        self.page()

        self.sidebar()

        _, risk = self.loader.load_all()

        risk, state, district = self.district_selection(risk)

        self.header()

        st.subheader(f"{district}, {state}")

        self.kpis(
            risk,
        )

        self.maps_section(
            risk,
        )

        self.charts_section(
            risk,
        )

        self.tables_section(
            risk,
        )

        self.footer()
