"""
==============================================================
Project SusBiome
Dashboard Models
==============================================================

Shared models and constants for the Dashboard.

Responsibilities
----------------
• Dashboard metadata
• Dataset locations
• Theme configuration
• Map defaults
• Color palette
• KPI definitions

This module intentionally contains NO Streamlit,
Plotly or business logic.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sources.common.config import PROJECT_ROOT


# ==========================================================
# DASHBOARD
# ==========================================================

DASHBOARD_NAME = "Project SusBiome Dashboard"

DASHBOARD_VERSION = "1.3.0"

PAGE_TITLE = "SusBiome Weather & Land Risk Outlook"

PAGE_ICON = "🌍"

LAYOUT = "wide"

SIDEBAR_STATE = "expanded"


# ==========================================================
# DATA
# ==========================================================

DATA_DIRECTORY = PROJECT_ROOT / "data"

PREDICTION_DATASET = (

    DATA_DIRECTORY

    / "prediction"

    / "predictions.parquet"

)

RISK_DATASET = (

    DATA_DIRECTORY

    / "risk"

    / "risk.parquet"

)

ASSESSMENT_DATASET = DATA_DIRECTORY / "serving" / "district_assessments.parquet"

LOCATIONS_DATASET = DATA_DIRECTORY / "raw" / "locations.csv"


# ==========================================================
# MAP
# ==========================================================

DEFAULT_LATITUDE = 20.5937

DEFAULT_LONGITUDE = 78.9629

DEFAULT_ZOOM = 4

MAP_HEIGHT = 650


# ==========================================================
# RISK COLORS
# ==========================================================

RISK_COLORS = {

    "NONE": "#2ECC71",

    "LOW": "#8BC34A",

    "MODERATE": "#FFC107",

    "HIGH": "#FF9800",

    "EXTREME": "#F44336",

    "VERY HIGH": "#F44336",

}


# ==========================================================
# KPI
# ==========================================================

KPI_COLUMNS = [

    "overall_risk_level",

    "flood_risk_level",

    "drought_risk_level",

    "cyclone_risk_level",

]


# ==========================================================
# TABLES
# ==========================================================

TABLE_COLUMNS = [

    "valid_time",

    "latitude",

    "longitude",

    "overall_risk_level",

    "dominant_hazard",

    "flood_probability",

    "drought_probability",

    "cyclone_probability",

]


# ==========================================================
# CHARTS
# ==========================================================

CHART_HEIGHT = 450

CHART_WIDTH = 900


# ==========================================================
# DATACLASSES
# ==========================================================

@dataclass(slots=True, frozen=True)
class DatasetStatus:
    """
    Dashboard dataset status.
    """

    prediction: bool

    risk: bool

    assessment: bool = False


@dataclass(slots=True, frozen=True)
class MapConfig:
    """
    Interactive map configuration.
    """

    latitude: float

    longitude: float

    zoom: int

    height: int


DEFAULT_MAP = MapConfig(

    latitude=DEFAULT_LATITUDE,

    longitude=DEFAULT_LONGITUDE,

    zoom=DEFAULT_ZOOM,

    height=MAP_HEIGHT,

)


# ==========================================================
# EXPORTS
# ==========================================================

__all__ = [

    "DASHBOARD_NAME",

    "DASHBOARD_VERSION",

    "PAGE_TITLE",

    "PAGE_ICON",

    "LAYOUT",

    "SIDEBAR_STATE",

    "PREDICTION_DATASET",

    "RISK_DATASET",

    "ASSESSMENT_DATASET",

    "LOCATIONS_DATASET",

    "DEFAULT_LATITUDE",

    "DEFAULT_LONGITUDE",

    "DEFAULT_ZOOM",

    "MAP_HEIGHT",

    "RISK_COLORS",

    "KPI_COLUMNS",

    "TABLE_COLUMNS",

    "CHART_HEIGHT",

    "CHART_WIDTH",

    "DatasetStatus",

    "MapConfig",

    "DEFAULT_MAP",

]
