"""Coordinate-based weather and land susceptibility assessment endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from scripts.serving.district_assessment import AssessmentUnavailableError
from scripts.serving.location_assessment import location_report

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get("/assessment")
def location_assessment(
    latitude: float = Query(ge=20.0, le=31.0),
    longitude: float = Query(ge=87.0, le=99.5),
    horizon_days: int = Query(default=7, enum=[3, 7, 14]),
) -> dict:
    try:
        return location_report(latitude, longitude, horizon_days)
    except (FileNotFoundError, AssessmentUnavailableError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
