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
from scripts.serving.planning_outlook import HAZARDS, OUTLOOK_HORIZONS, build_planning_outlook
from scripts.dashboard.operational_visuals import (
    HAZARD_COLORS,
    HAZARD_LABELS,
    hazard_bar_chart,
    horizon_line_chart,
    risk_map,
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
        st.markdown(
            """
<style>
    :root { color-scheme: light; }
    .stApp { background: #F5F7FA; color: #0B1530; }
    .block-container { max-width: 1500px; padding-top: 1.8rem; padding-bottom: 2rem; }
    h1, h2, h3, p { letter-spacing: 0; }
    [data-testid="stSidebar"] { background: #101B33; border-right: 1px solid #24324D; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label { color: #F8FAFC !important; }
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: #FFFFFF; border-color: #CBD5E1; color: #0B1530;
    }
    [data-testid="stSidebar"] [role="radiogroup"] { background: #17233D; padding: 3px; }
    [data-testid="stSidebar"] button[data-testid="stBaseButton-segmented_control"] p {
        color: #475569 !important;
    }
    [data-testid="stSidebar"] button[data-testid="stBaseButton-segmented_controlActive"] p {
        color: #FFFFFF !important;
    }
    [data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid #D9E1EC; border-radius: 4px; padding: 1rem 1.1rem;
    }
    [data-testid="stMetricLabel"] { color: #64748B; text-transform: uppercase; }
    [data-testid="stMetricValue"] { color: #0B1530; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF; border-color: #D9E1EC; border-radius: 4px;
    }
    .susbiome-brand { color: #91A4C3; font-size: 0.72rem; letter-spacing: 0.22em; }
    .susbiome-sidebar-title { color: #FFFFFF; font-size: 1.35rem; font-weight: 700; margin-top: 0.2rem; }
    .location-eyebrow { color: #6B7C99; font-size: 0.76rem; letter-spacing: 0.22em; text-transform: uppercase; }
    .location-title { color: #0B1530; font-size: 2.65rem; line-height: 1.05; font-weight: 750; margin: 0.25rem 0 0.45rem; }
    .location-meta { color: #64748B; font-size: 0.98rem; }
    .section-eyebrow { color: #6B7C99; font-size: 0.72rem; letter-spacing: 0.2em; text-transform: uppercase; }
    .section-title { color: #0B1530; font-size: 1.45rem; font-weight: 700; margin: 0.15rem 0 0.8rem; }
    .risk-tile { background: #FFFFFF; border: 1px solid #D9E1EC; border-radius: 4px; padding: 0.95rem 1rem; min-height: 96px; }
    .risk-tile-label { color: #64748B; font-size: 0.72rem; letter-spacing: 0.16em; text-transform: uppercase; }
    .risk-tile-value { color: #0B1530; font-size: 1.75rem; font-weight: 750; margin-top: 0.3rem; }
    .risk-tile-level { color: #64748B; font-size: 0.75rem; margin-left: 0.45rem; }
    .composite-card { background: #FFFFFF; border: 1px solid #D9E1EC; border-radius: 4px; padding: 1rem 1.15rem; min-height: 96px; }
    .composite-label { color: #64748B; font-size: 0.72rem; letter-spacing: 0.16em; text-transform: uppercase; }
    .composite-value { color: #0B1530; font-size: 2rem; font-weight: 750; margin-top: 0.35rem; }
    .composite-level { color: #64748B; font-size: 0.76rem; margin-left: 0.5rem; text-transform: uppercase; }
    @media (max-width: 760px) {
        .block-container { padding: 1rem 0.8rem 1.5rem; }
        .location-title { font-size: 2rem; }
        .section-title { font-size: 1.2rem; }
    }
</style>
""",
            unsafe_allow_html=True,
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

        st.sidebar.markdown(
            '<div class="susbiome-brand">NORTHEAST INDIA</div>'
            '<div class="susbiome-sidebar-title">SusBiome</div>',
            unsafe_allow_html=True,
        )
        st.sidebar.divider()

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
        """Render the map-first operational planning outlook."""
        assessment = self.loader.assessment()
        outlook = build_planning_outlook(assessment)
        locations = self.loader.locations()

        states = locations["state"].drop_duplicates().tolist()
        state = st.sidebar.selectbox("State", states)
        districts = locations.loc[locations["state"].eq(state), "district"].tolist()
        district = st.sidebar.selectbox("District", districts)
        horizon = int(
            st.sidebar.segmented_control(
                "Outlook horizon", list(OUTLOOK_HORIZONS), default=30,
                format_func=lambda value: f"{value}d",
            )
        )
        st.sidebar.caption("Planning outlook · not a disaster probability")

        location = locations.loc[
            locations["state"].eq(state) & locations["district"].eq(district)
        ].iloc[0]
        district_outlook = outlook.loc[
            outlook["state"].eq(state) & outlook["district"].eq(district)
        ].sort_values("outlook_horizon_days")
        selected = district_outlook.loc[
            district_outlook["outlook_horizon_days"].eq(horizon)
        ].iloc[0]
        state_outlook = outlook.loc[
            outlook["state"].eq(state) & outlook["outlook_horizon_days"].eq(horizon)
        ]

        heading, composite = st.columns([4, 1.25], vertical_alignment="bottom")
        with heading:
            st.markdown(
                f'<div class="location-eyebrow">{state}</div>'
                f'<h1 class="location-title">{district}</h1>'
                f'<div class="location-meta">{float(location["latitude"]):.3f}°N, '
                f'{float(location["longitude"]):.3f}°E · {horizon}-day planning outlook</div>',
                unsafe_allow_html=True,
            )
        with composite:
            st.markdown(
                '<div class="composite-card">'
                '<div class="composite-label">Composite risk</div>'
                f'<div class="composite-value">{float(selected["composite_risk_score"]):.0f}'
                f'<span class="composite-level">{selected["composite_risk_level"]}</span>'
                '</div></div>',
                unsafe_allow_html=True,
            )

        st.write("")
        with st.container(border=True):
            st.markdown(
                f'<div class="section-eyebrow">{state.upper()} RISK MAP</div>'
                f'<div class="section-title">District outlook · {horizon} days</div>',
                unsafe_allow_html=True,
            )
            st.pydeck_chart(
                risk_map(state, district, state_outlook, location),
                width="stretch",
                height=470,
            )

        risk_columns = st.columns(3)
        for column, hazard in zip(risk_columns, HAZARDS, strict=True):
            label = HAZARD_LABELS[hazard]
            score = float(selected[f"{hazard}_outlook_score"])
            level = str(selected[f"{hazard}_outlook_level"]).title()
            color = HAZARD_COLORS[label]
            with column:
                st.markdown(
                    f'<div class="risk-tile" style="border-top: 4px solid {color}">'
                    f'<div class="risk-tile-label">{label}</div>'
                    f'<div class="risk-tile-value">{score:.0f}'
                    f'<span class="risk-tile-level">{level}</span></div></div>',
                    unsafe_allow_html=True,
                )

        st.write("")
        bar_column, line_column = st.columns(2)
        with bar_column:
            with st.container(border=True):
                st.markdown(
                    '<div class="section-eyebrow">THREE-HAZARD OUTLOOK</div>'
                    f'<div class="section-title">{horizon}-day risk scores</div>',
                    unsafe_allow_html=True,
                )
                st.altair_chart(
                    hazard_bar_chart(district_outlook, horizon), width="stretch"
                )
        with line_column:
            with st.container(border=True):
                st.markdown(
                    '<div class="section-eyebrow">RISK ACROSS HORIZONS</div>'
                    '<div class="section-title">15 → 30 → 60 → 90 days</div>',
                    unsafe_allow_html=True,
                )
                st.altair_chart(horizon_line_chart(district_outlook), width="stretch")

        with st.expander("Assessment details, actions, and sources"):
            details = st.columns(3)
            details[0].metric("Confidence", selected["outlook_confidence"])
            details[1].metric("Dominant hazard", str(selected["dominant_hazard"]).title())
            details[2].metric("Static coverage", f"{100 * selected['static_factor_coverage']:.0f}%")
            for action in json.loads(selected["mitigation_actions"]):
                st.markdown(f"- {action}")
            st.warning(DISCLAIMER)
            st.caption(
                "15 days uses the current near-term assessment. Longer horizons gradually "
                "transition toward the district historical susceptibility baseline."
            )
            for source in SOURCES:
                st.markdown(
                    f"**{source['name']}** · {source['role']}  \n"
                    f"[{source['license']}]({source['url']})"
                )

        st.caption(
            "Risk scale · "
            + " · ".join(
                f"{item['level'].title()} {item['minimum']:g}–{item['maximum']:g}"
                for item in RISK_SCALE
            )
        )
        self.footer()
