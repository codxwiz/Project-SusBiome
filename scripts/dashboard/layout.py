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

import json

import pandas as pd
import streamlit as st  # type: ignore

from scripts.dashboard.loader import (
    DashboardLoader,
)

from scripts.dashboard.models import (
    DASHBOARD_NAME,
    DASHBOARD_VERSION,
    LAYOUT,
    PAGE_ICON,
    PAGE_TITLE,
    SIDEBAR_STATE,
)

class DashboardLayout:
    """
    Dashboard layout.
    """

    def __init__(
        self,
    ) -> None:

        self.loader = DashboardLoader()
        self.maps = None
        self.charts = None
        self.tables = None
        if not self.loader.status().assessment:
            from scripts.dashboard.charts import DashboardCharts
            from scripts.dashboard.maps import DashboardMaps
            from scripts.dashboard.tables import DashboardTables

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

        if self.loader.status().assessment:
            self.operational_build()
            return

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

    def operational_build(self) -> None:
        """Render the district-first operational assessment."""
        assessment = self.loader.assessment()
        assessment, state, district = self.district_selection(assessment)
        horizons = sorted(assessment["horizon_days"].astype(int).unique().tolist())
        horizon = st.sidebar.segmented_control(
            "Forecast horizon", horizons, default=7 if 7 in horizons else horizons[0]
        )
        row = assessment.loc[assessment["horizon_days"].eq(int(horizon))].iloc[0]

        self.header()
        st.subheader(f"{district}, {state}")
        st.caption(f"{int(horizon)}-day outlook through {pd.Timestamp(row['valid_to']).date()}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Rainfall", f"{row['precipitation_sum_mm']:.1f} mm")
        col2.metric("Maximum gust", f"{row['wind_gust_max_kmh']:.1f} km/h")
        col3.metric("Confidence", row["confidence_grade"])
        col4.metric(
            "Model assessment", "Available" if row["assessment_available"] else "Pending"
        )

        overview, factors, guidance = st.tabs(["Outlook", "Factors", "Actions"])
        with overview:
            signal = pd.DataFrame(
                {
                    "Hazard": ["Flood", "Cyclone", "Drought"],
                    "Forecast signal": [
                        row["flood_forecast_signal"],
                        row["cyclone_forecast_signal"],
                        row["drought_forecast_signal"],
                    ],
                    "Risk level": [
                        row["flood_risk_level"],
                        row["cyclone_risk_level"],
                        row["drought_risk_level"],
                    ],
                }
            )
            st.dataframe(signal, hide_index=True, width="stretch")
            st.caption(row["confidence_reason"])
        with factors:
            factor_data = pd.DataFrame(
                {
                    "Factor": [
                        "Flood susceptibility", "Cyclone susceptibility",
                        "Drought susceptibility", "Static factor coverage",
                        "Boundary support",
                    ],
                    "Value": [
                        f"{row['flood_susceptibility']:.2f}",
                        f"{row['cyclone_susceptibility']:.2f}",
                        f"{row['drought_susceptibility']:.2f}",
                        f"{100 * row['static_factor_coverage']:.0f}%",
                        row["boundary_status"],
                    ],
                }
            )
            st.dataframe(factor_data, hide_index=True, width="stretch")
        with guidance:
            for action in json.loads(row["mitigation_actions"]):
                st.markdown(f"- {action}")
            st.warning(
                "Decision-support estimate, not an official warning. Follow IMD and local authorities."
            )

        self.footer()
