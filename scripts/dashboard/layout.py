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
from scripts.serving.attribution import DISCLAIMER, RISK_SCALE, SOURCES
from scripts.serving.location_assessment import location_report

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

            "Flood • Cyclone • Drought "

            "Weather & Land Risk Outlook"

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
        horizons = sorted(assessment["horizon_days"].astype(int).unique().tolist())
        area_mode = st.sidebar.segmented_control(
            "Assessment area", ["District", "Land coordinates"], default="District"
        )
        horizon = st.sidebar.segmented_control(
            "Forecast horizon", horizons, default=7 if 7 in horizons else horizons[0]
        )
        point_report = None
        if area_mode == "Land coordinates":
            latitude = st.sidebar.number_input(
                "Latitude", min_value=20.0, max_value=31.0, value=27.48, step=0.01
            )
            longitude = st.sidebar.number_input(
                "Longitude", min_value=87.0, max_value=99.5, value=94.91, step=0.01
            )
            try:
                point_report = location_report(float(latitude), float(longitude), int(horizon))
            except ValueError as error:
                st.error(str(error))
                st.stop()
            state = point_report["district_match"]["state"]
            district = point_report["district_match"]["district"]
            row = assessment.loc[
                assessment["state"].eq(state)
                & assessment["district"].eq(district)
                & assessment["horizon_days"].eq(int(horizon))
            ].iloc[0]
        else:
            assessment, state, district = self.district_selection(assessment)
            row = assessment.loc[assessment["horizon_days"].eq(int(horizon))].iloc[0]

        self.header()
        title = f"{district}, {state}"
        if point_report:
            title = f"Selected land · {title}"
        st.subheader(title)
        st.caption(f"{int(horizon)}-day outlook through {pd.Timestamp(row['valid_to']).date()}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Rainfall", f"{row['precipitation_sum_mm']:.1f} mm")
        col2.metric("Maximum gust", f"{row['wind_gust_max_kmh']:.1f} km/h")
        confidence_grade = (
            point_report["confidence"]["grade"] if point_report else row["confidence_grade"]
        )
        col3.metric("Confidence", confidence_grade)
        col4.metric(
            "Weather assessment", "Available" if row["assessment_available"] else "Pending"
        )

        overview, factors, guidance = st.tabs(["Outlook", "Factors", "Actions"])
        with overview:
            point_hazards = point_report["hazards"] if point_report else None
            signal = pd.DataFrame(
                {
                    "Hazard": ["Flood", "Cyclone", "Drought"],
                    "Risk score": [
                        point_hazards["flood"]["weather_land_risk_score"]
                        if point_hazards else row["flood_weather_risk_score"],
                        point_hazards["cyclone"]["weather_land_risk_score"]
                        if point_hazards else row["cyclone_weather_risk_score"],
                        point_hazards["drought"]["weather_land_risk_score"]
                        if point_hazards else row["drought_weather_risk_score"],
                    ],
                    "Risk level": [
                        point_hazards["flood"]["risk_level"]
                        if point_hazards else row["flood_risk_level"],
                        point_hazards["cyclone"]["risk_level"]
                        if point_hazards else row["cyclone_risk_level"],
                        point_hazards["drought"]["risk_level"]
                        if point_hazards else row["drought_risk_level"],
                    ],
                }
            )
            st.dataframe(signal, hide_index=True, width="stretch")
            st.caption(
                "Risk scale: "
                + " · ".join(
                    f"{item['level'].title()} {item['minimum']:g}–{item['maximum']:g}"
                    for item in RISK_SCALE
                )
            )
            st.caption(
                point_report["confidence"]["reason"] if point_report else row["confidence_reason"]
            )
        with factors:
            factor_names = [
                "Flood susceptibility", "Cyclone susceptibility",
                "Drought susceptibility", "Static factor coverage",
                "District mean elevation", "District mean slope",
                "Dominant sampled land cover",
                "Boundary support", "IMD cyclone bulletin",
                "GPM/CHIRPS daily correlation",
            ]
            factor_values = [
                f"{row['flood_susceptibility']:.2f}",
                f"{row['cyclone_susceptibility']:.2f}",
                f"{row['drought_susceptibility']:.2f}",
                f"{100 * row['static_factor_coverage']:.0f}%",
                f"{row['elevation_mean_m']:.0f} m",
                (
                    f"{row['slope_mean_degrees']:.1f}°"
                    if pd.notna(row.get("slope_mean_degrees")) else "Unavailable"
                ),
                str(row.get("dominant_land_cover_class", "Unavailable")).replace(
                    "_", " "
                ).title(),
                row["boundary_status"],
                row["cyclone_confirmation_status"],
                (
                    f"{row['chirps_gpm_correlation']:.2f}"
                    if pd.notna(row["chirps_gpm_correlation"])
                    else "Unavailable"
                ),
            ]
            if point_report:
                terrain = point_report["land_context"]["terrain"]
                land_cover = point_report["land_context"]["land_cover"]
                factor_names.extend(["Point elevation", "Point slope", "Point land cover"])
                factor_values.extend(
                    [
                        f"{terrain['elevation_m']:.0f} m" if terrain else "Unavailable",
                        f"{terrain['slope_degrees']:.1f}°" if terrain else "Unavailable",
                        land_cover["class_name"].replace("_", " ").title()
                        if land_cover else "Unavailable",
                    ]
                )
            factor_data = pd.DataFrame(
                {
                    "Factor": factor_names,
                    "Value": factor_values,
                }
            )
            st.dataframe(factor_data, hide_index=True, width="stretch")
        with guidance:
            for action in json.loads(row["mitigation_actions"]):
                st.markdown(f"- {action}")
            st.warning(
                DISCLAIMER
            )
            with st.expander("Data sources and attribution"):
                for source in SOURCES:
                    st.markdown(
                        f"**{source['name']}** — {source['role']}  \n"
                        f"[{source['license']}]({source['url']})"
                    )

        self.footer()
