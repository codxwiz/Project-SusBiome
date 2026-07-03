"""Map and chart builders for the operational three-hazard dashboard."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk

from scripts.serving.planning_outlook import HAZARDS
from scripts.sources.common.config import PROJECT_ROOT

BOUNDARIES_PATH = PROJECT_ROOT / "data/silver/geospatial/ne_district_boundaries.geojson"

HAZARD_LABELS = {"flood": "Flood", "drought": "Drought", "cyclone": "Cyclone"}
HAZARD_COLORS = {"Flood": "#2B59D9", "Drought": "#C66708", "Cyclone": "#13857F"}
RISK_COLORS = {
    "LOW": [42, 157, 111, 190],
    "MODERATE": [233, 196, 106, 205],
    "HIGH": [244, 153, 97, 215],
    "VERY HIGH": [196, 61, 78, 225],
    "UNAVAILABLE": [148, 163, 184, 160],
}


def risk_color(level: str) -> list[int]:
    return RISK_COLORS.get(str(level).upper(), RISK_COLORS["UNAVAILABLE"])


def state_geojson(state: str, outlook: pd.DataFrame, selected_district: str) -> dict:
    payload = json.loads(Path(BOUNDARIES_PATH).read_text(encoding="utf-8"))
    scores = outlook.set_index(["state", "district"]).to_dict("index")
    features = []
    for source in payload.get("features", []):
        properties = source.get("properties", {})
        if properties.get("state") != state:
            continue
        district = str(properties.get("district"))
        row = scores.get((state, district))
        if row is None:
            continue
        feature = copy.deepcopy(source)
        selected = district == selected_district
        feature["properties"].update(
            {
                "composite_score": float(row["composite_risk_score"]),
                "risk_level": str(row["composite_risk_level"]),
                "dominant_hazard": str(row["dominant_hazard"]).title(),
                "fill_color": risk_color(str(row["composite_risk_level"])),
                "line_color": [11, 21, 48, 255] if selected else [255, 255, 255, 220],
                "line_width": 5 if selected else 1,
            }
        )
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}


def risk_map(
    state: str,
    district: str,
    outlook: pd.DataFrame,
    selected_location: pd.Series,
) -> pdk.Deck:
    geojson = state_geojson(state, outlook, district)
    layers = [
        pdk.Layer(
            "GeoJsonLayer",
            geojson,
            pickable=True,
            stroked=True,
            filled=True,
            get_fill_color="properties.fill_color",
            get_line_color="properties.line_color",
            get_line_width="properties.line_width",
            line_width_min_pixels=1,
            opacity=0.82,
        ),
        pdk.Layer(
            "ScatterplotLayer",
            [
                {
                    "latitude": float(selected_location["latitude"]),
                    "longitude": float(selected_location["longitude"]),
                }
            ],
            get_position="[longitude, latitude]",
            get_radius=4500,
            radius_min_pixels=6,
            radius_max_pixels=11,
            get_fill_color=[11, 21, 48, 235],
            get_line_color=[255, 255, 255, 255],
            line_width_min_pixels=2,
            stroked=True,
            pickable=False,
        ),
    ]
    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=float(selected_location["latitude"]),
            longitude=float(selected_location["longitude"]),
            zoom=6.3,
            min_zoom=4,
            max_zoom=10,
            pitch=0,
        ),
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        tooltip={
            "html": (
                "<b>{district}</b><br/>Composite risk: {composite_score}<br/>"
                "Level: {risk_level}<br/>Dominant: {dominant_hazard}"
            ),
            "style": {"backgroundColor": "#0B1530", "color": "white"},
        },
    )


def selected_hazard_frame(outlook: pd.DataFrame, horizon: int) -> pd.DataFrame:
    selected = outlook.loc[outlook["outlook_horizon_days"].eq(horizon)].iloc[0]
    return pd.DataFrame(
        {
            "Hazard": [HAZARD_LABELS[hazard] for hazard in HAZARDS],
            "Risk score": [float(selected[f"{hazard}_outlook_score"]) for hazard in HAZARDS],
            "Risk level": [str(selected[f"{hazard}_outlook_level"]) for hazard in HAZARDS],
        }
    )


def hazard_bar_chart(outlook: pd.DataFrame, horizon: int) -> alt.Chart:
    frame = selected_hazard_frame(outlook, horizon)
    return (
        alt.Chart(frame)
        .mark_bar(size=56, cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X("Hazard:N", sort=["Flood", "Drought", "Cyclone"], title=None),
            y=alt.Y("Risk score:Q", scale=alt.Scale(domain=[0, 100]), title="Risk score"),
            color=alt.Color(
                "Hazard:N",
                scale=alt.Scale(
                    domain=list(HAZARD_COLORS), range=list(HAZARD_COLORS.values())
                ),
                legend=None,
            ),
            tooltip=["Hazard:N", alt.Tooltip("Risk score:Q", format=".1f"), "Risk level:N"],
        )
        .properties(height=320)
        .configure_axis(gridColor="#E2E8F0", labelColor="#64748B", titleColor="#334155")
        .configure_view(stroke=None)
    )


def horizon_line_chart(outlook: pd.DataFrame) -> alt.Chart:
    records = []
    for row in outlook.itertuples(index=False):
        for hazard in HAZARDS:
            records.append(
                {
                    "Horizon": int(row.outlook_horizon_days),
                    "Hazard": HAZARD_LABELS[hazard],
                    "Risk score": float(getattr(row, f"{hazard}_outlook_score")),
                }
            )
    frame = pd.DataFrame(records)
    line = (
        alt.Chart(frame)
        .mark_line(point=alt.OverlayMarkDef(size=70), strokeWidth=3)
        .encode(
            x=alt.X(
                "Horizon:O", sort=[15, 30, 60, 90], title="Outlook horizon (days)"
            ),
            y=alt.Y("Risk score:Q", scale=alt.Scale(domain=[0, 100]), title="Risk score"),
            color=alt.Color(
                "Hazard:N",
                scale=alt.Scale(
                    domain=list(HAZARD_COLORS), range=list(HAZARD_COLORS.values())
                ),
                legend=alt.Legend(orient="bottom", direction="horizontal", title=None),
            ),
            tooltip=["Hazard:N", "Horizon:O", alt.Tooltip("Risk score:Q", format=".1f")],
        )
        .properties(height=320)
    )
    return (
        line.configure_axis(
            gridColor="#E2E8F0", labelColor="#64748B", titleColor="#334155"
        ).configure_view(stroke=None)
    )

