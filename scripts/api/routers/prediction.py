"""
==============================================================
Project SusBiome
Prediction Router
==============================================================

Prediction API endpoints.

Responsibilities
----------------
• Execute Prediction Service
• Predict from uploaded dataset
• Return prediction summary
• Save prediction output

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from scripts.api.dependencies import (
    get_prediction_orchestrator,
    require_api_key,
)

from scripts.api.models import (
    DEFAULT_FEATURE_FILE,
    DEFAULT_PREDICTION_FILE,
    resolve_data_path,
)

from scripts.prediction.orchestrator import (
    PredictionOrchestrator,
)

router = APIRouter(

    prefix="/prediction",

    tags=[

        "Prediction",

    ],

)


# ==========================================================
# DEFAULT INPUT
# ==========================================================

DEFAULT_INPUT = DEFAULT_FEATURE_FILE


# ==========================================================
# PREDICT
# ==========================================================

@router.post(
    "",
)
def predict(

    input_path: str | None = None,

    output_path: str | None = None,

    _authorization: None = Depends(require_api_key),

    pipeline: PredictionOrchestrator = Depends(

        get_prediction_orchestrator,

    ),

) -> dict:
    """
    Run prediction pipeline.
    """

    try:
        source = resolve_data_path(input_path, default=DEFAULT_INPUT)
        destination = resolve_data_path(
            output_path, default=DEFAULT_PREDICTION_FILE, output=True
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if not source.exists():

        raise HTTPException(

            status_code=404,

            detail=f"Input dataset not found: {source}",

        )

    try:
        predictions, summary = pipeline.run(
            input_path=source,
            output_path=destination,
        )
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return {

        "status": "OK",

        "rows": len(

            predictions,

        ),

        "output": str(

            destination,

        ),

        "summary": summary,

    }


# ==========================================================
# SUMMARY
# ==========================================================

@router.get(
    "/summary",
)
def summary(

    pipeline: PredictionOrchestrator = Depends(

        get_prediction_orchestrator,

    ),

) -> dict:
    """
    Prediction dataset summary.
    """

    path = DEFAULT_PREDICTION_FILE

    if not path.exists():

        raise HTTPException(

            status_code=404,

            detail="Prediction dataset not found.",

        )

    dataframe = pipeline.load(

        path,

    )

    report = pipeline.report(

        dataframe,

    )

    return {

        "status": "OK",

        "dataset": str(

            path,

        ),

        "summary": report,

    }


# ==========================================================
# EXISTS
# ==========================================================

@router.get(
    "/exists",
)
def exists() -> dict:
    """
    Check whether prediction output exists.
    """

    return {

        "exists": DEFAULT_PREDICTION_FILE.exists(),

        "path": str(

            DEFAULT_PREDICTION_FILE,

        ),

    }


# ==========================================================
# INFO
# ==========================================================

@router.get(
    "/info",
)
def info() -> dict:
    """
    Prediction service information.
    """

    return {

        "service": "Prediction Service",

        "input": str(

            DEFAULT_INPUT,

        ),

        "default_output": str(

            DEFAULT_PREDICTION_FILE,

        ),

        "endpoints": [

            "POST /prediction",

            "GET /prediction/summary",

            "GET /prediction/exists",

            "GET /prediction/info",

        ],

    }
