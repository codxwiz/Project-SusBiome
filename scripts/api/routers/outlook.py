"""Static planning-outlook API used by the production frontend."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from scripts.sources.common.config import PROJECT_ROOT

OUTLOOK_PAYLOAD_PATH = PROJECT_ROOT / "frontend/public/data/susbiome-outlook.json"
BOUNDARIES_PATH = PROJECT_ROOT / "frontend/public/data/ne-district-boundaries.geojson"

router = APIRouter(prefix="/outlook", tags=["Outlook"])


@lru_cache(maxsize=1)
def _payload() -> dict:
    if not OUTLOOK_PAYLOAD_PATH.exists():
        raise FileNotFoundError("Frontend outlook payload is not available.")
    return json.loads(OUTLOOK_PAYLOAD_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _boundaries() -> dict:
    if not BOUNDARIES_PATH.exists():
        raise FileNotFoundError("Frontend boundary payload is not available.")
    return json.loads(BOUNDARIES_PATH.read_text(encoding="utf-8"))


def _load_payload() -> dict:
    try:
        return _payload()
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("")
def outlook() -> dict:
    """Return the complete static production outlook bundle."""
    return _load_payload()


@router.get("/meta")
def meta() -> dict:
    """Return frontend metadata, source attribution, and public wording."""
    return _load_payload()["meta"]


@router.get("/districts")
def districts(state: str | None = None) -> dict:
    """List supported Northeast India districts."""
    payload = _load_payload()
    records = payload["districts"]
    if state:
        records = [
            row for row in records
            if str(row["state"]).casefold() == state.casefold()
        ]
        if not records:
            raise HTTPException(status_code=404, detail="State not found.")
    return {"count": len(records), "districts": records}


@router.get("/boundaries")
def boundaries(state: str | None = None) -> dict:
    """Return frontend district boundaries, optionally filtered by state."""
    try:
        payload = _boundaries()
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if not state:
        return payload
    features = [
        feature for feature in payload.get("features", [])
        if str(feature.get("properties", {}).get("state", "")).casefold() == state.casefold()
    ]
    if not features:
        raise HTTPException(status_code=404, detail="State not found.")
    return {"type": "FeatureCollection", "features": features}


@router.get("/{state}/{district}")
def district_outlook(
    state: str,
    district: str,
    horizon: int | None = Query(default=None, enum=[15, 30, 60, 90]),
) -> dict:
    """Return all horizons, or one selected horizon, for a district."""
    payload = _load_payload()
    records = [
        row for row in payload["outlook"]
        if str(row["state"]).casefold() == state.casefold()
        and str(row["district"]).casefold() == district.casefold()
    ]
    if not records:
        raise HTTPException(status_code=404, detail="District not found.")
    records = sorted(records, key=lambda row: int(row["horizon"]))
    if horizon is not None:
        records = [row for row in records if int(row["horizon"]) == horizon]
        if not records:
            raise HTTPException(status_code=404, detail="Horizon not found.")
    selected = next(
        row for row in payload["districts"]
        if str(row["state"]).casefold() == state.casefold()
        and str(row["district"]).casefold() == district.casefold()
    )
    return {
        "state": selected["state"],
        "district": selected["district"],
        "location": selected,
        "meta": payload["meta"],
        "outlook": records,
    }
