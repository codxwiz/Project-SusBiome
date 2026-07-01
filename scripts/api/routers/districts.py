"""Read-only district registry, forecast, and assessment endpoints."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from scripts.geospatial.districts import MANIFEST_PATH
from scripts.serving.district_assessment import ASSESSMENT_PATH, district_report

router = APIRouter(prefix="/districts", tags=["Districts"])


def _assessment() -> pd.DataFrame:
    if not ASSESSMENT_PATH.exists():
        raise HTTPException(status_code=503, detail="District serving dataset is not available.")
    return pd.read_parquet(ASSESSMENT_PATH)


def _select(dataframe: pd.DataFrame, state: str, district: str) -> pd.DataFrame:
    selected = dataframe.loc[
        dataframe["state"].str.casefold().eq(state.casefold())
        & dataframe["district"].str.casefold().eq(district.casefold())
    ]
    if selected.empty:
        raise HTTPException(status_code=404, detail="District not found.")
    return selected


@router.get("")
def list_districts(state: str | None = None) -> dict:
    if not Path(MANIFEST_PATH).exists():
        raise HTTPException(status_code=503, detail="District boundary registry is not available.")
    registry = pd.read_csv(MANIFEST_PATH)
    if state:
        registry = registry.loc[registry["state"].str.casefold().eq(state.casefold())]
        if registry.empty:
            raise HTTPException(status_code=404, detail="State not found.")
    columns = [
        "state", "district", "latitude", "longitude", "boundary_status",
        "district_wide_usable", "boundary_year",
    ]
    records = registry[columns].where(pd.notna(registry[columns]), None).to_dict("records")
    return {"count": len(records), "districts": records}


@router.get("/{state}/{district}/forecast")
def district_forecast(
    state: str,
    district: str,
    horizon_days: int = Query(default=7, enum=[3, 7, 14]),
) -> dict:
    row = _select(_assessment(), state, district)
    row = row.loc[row["horizon_days"].eq(horizon_days)]
    if row.empty:
        raise HTTPException(status_code=404, detail="Forecast horizon not found.")
    report = district_report(row.iloc[0])
    return {
        "state": report["state"],
        "district": report["district"],
        "horizon_days": report["horizon_days"],
        "valid_from": report["valid_from"],
        "valid_to": report["valid_to"],
        "forecast": report["forecast"],
        "signals": {
            hazard: details["forecast_signal"] for hazard, details in report["hazards"].items()
        },
        "disclaimer": report["disclaimer"],
    }


@router.get("/{state}/{district}/assessment")
def district_assessment(
    state: str,
    district: str,
    horizon_days: int = Query(default=7, enum=[3, 7, 14]),
) -> dict:
    selected = _select(_assessment(), state, district)
    selected = selected.loc[selected["horizon_days"].eq(horizon_days)]
    if selected.empty:
        raise HTTPException(status_code=404, detail="Assessment horizon not found.")
    return district_report(selected.iloc[0])


@router.get("/{state}/{district}/report")
def district_horizon_report(state: str, district: str) -> dict:
    selected = _select(_assessment(), state, district).sort_values("horizon_days")
    reports = [district_report(row) for _, row in selected.iterrows()]
    return {
        "state": reports[0]["state"],
        "district": reports[0]["district"],
        "reports": reports,
    }
