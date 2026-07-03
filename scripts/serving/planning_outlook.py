"""Build transparent 15, 30, 60, and 90 day planning outlook scores."""

from __future__ import annotations

import pandas as pd

from scripts.serving.district_assessment import _level

OUTLOOK_HORIZONS = (15, 30, 60, 90)
FORECAST_WEIGHTS = {15: 0.95, 30: 0.75, 60: 0.50, 90: 0.30}
HAZARDS = ("flood", "drought", "cyclone")


def build_planning_outlook(assessment: pd.DataFrame) -> pd.DataFrame:
    """Blend the longest current forecast with district susceptibility by horizon."""
    required = {
        "state",
        "district",
        "horizon_days",
        "valid_from",
        *{
            f"{hazard}_{field}"
            for hazard in HAZARDS
            for field in ("weather_risk_score", "susceptibility")
        },
    }
    missing = required - set(assessment.columns)
    if missing:
        raise ValueError("Assessment is missing: " + ", ".join(sorted(missing)))
    longest = assessment.loc[assessment["horizon_days"].eq(14)].copy()
    if longest.empty:
        maximum = int(assessment["horizon_days"].max())
        longest = assessment.loc[assessment["horizon_days"].eq(maximum)].copy()
    if longest.duplicated(["state", "district"]).any():
        raise ValueError("Assessment contains duplicate district horizon rows.")

    frames = []
    for horizon in OUTLOOK_HORIZONS:
        frame = longest.copy()
        forecast_weight = FORECAST_WEIGHTS[horizon]
        frame["outlook_horizon_days"] = horizon
        frame["forecast_weight"] = forecast_weight
        frame["historical_weight"] = 1 - forecast_weight
        for hazard in HAZARDS:
            current = pd.to_numeric(frame[f"{hazard}_weather_risk_score"], errors="coerce")
            baseline = 100 * pd.to_numeric(
                frame[f"{hazard}_susceptibility"], errors="coerce"
            )
            score = (forecast_weight * current + (1 - forecast_weight) * baseline).clip(0, 100)
            frame[f"{hazard}_outlook_score"] = score.round(1)
            frame[f"{hazard}_outlook_level"] = frame[f"{hazard}_outlook_score"].map(_level)
        score_columns = [f"{hazard}_outlook_score" for hazard in HAZARDS]
        frame["composite_risk_score"] = (
            0.60 * frame[score_columns].max(axis=1)
            + 0.40 * frame[score_columns].mean(axis=1)
        ).round(1)
        frame["composite_risk_level"] = frame["composite_risk_score"].map(_level)
        frame["dominant_hazard"] = (
            frame[score_columns]
            .idxmax(axis=1)
            .str.replace("_outlook_score", "", regex=False)
            .str.upper()
        )
        frame["outlook_confidence"] = "B" if horizon <= 30 else "C"
        frame["outlook_method"] = "forecast_to_historical_susceptibility_blend_v1"
        frame["outlook_is_probability"] = False
        frame["valid_to"] = pd.to_datetime(frame["valid_from"]) + pd.to_timedelta(
            horizon - 1, unit="D"
        )
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)
