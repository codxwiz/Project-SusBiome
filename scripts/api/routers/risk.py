"""
==============================================================
Project SusBiome
Risk Router
==============================================================

Risk API endpoints.

Responsibilities
----------------
• Execute Risk Engine
• Generate Risk Dataset
• Return Risk Summary
• Save Risk Output

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from scripts.api.dependencies import (
    get_risk_orchestrator,
    require_api_key,
)

from scripts.api.models import (
    DEFAULT_PREDICTION_FILE,
    DEFAULT_RISK_FILE,
    resolve_data_path,
)

from scripts.risk.orchestrator import (
    RiskOrchestrator,
)

router = APIRouter(

    prefix="/risk",

    tags=[

        "Risk",

    ],

)


# ==========================================================
# BUILD RISK
# ==========================================================

@router.post(
    "",
)
def build_risk(

    input_path: str | None = None,

    output_path: str | None = None,

    _authorization: None = Depends(require_api_key),

    pipeline: RiskOrchestrator = Depends(

        get_risk_orchestrator,

    ),

) -> dict:
    """
    Execute Risk Engine.
    """

    try:
        source = resolve_data_path(input_path, default=DEFAULT_PREDICTION_FILE)
        destination = resolve_data_path(
            output_path, default=DEFAULT_RISK_FILE, output=True
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if not source.exists():

        raise HTTPException(

            status_code=404,

            detail=f"Prediction dataset not found: {source}",

        )

    try:
        dataframe, summary = pipeline.run(
            input_path=source,
            output_path=destination,
        )
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return {

        "status": "OK",

        "rows": len(

            dataframe,

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

    pipeline: RiskOrchestrator = Depends(

        get_risk_orchestrator,

    ),

) -> dict:
    """
    Risk summary.
    """

    if not DEFAULT_RISK_FILE.exists():

        raise HTTPException(

            status_code=404,

            detail="Risk dataset not found.",

        )

    dataframe = pipeline.load(

        DEFAULT_RISK_FILE,

    )

    report = pipeline.report(

        dataframe,

    )

    return {

        "status": "OK",

        "dataset": str(

            DEFAULT_RISK_FILE,

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
    Check Risk dataset.
    """

    return {

        "exists": DEFAULT_RISK_FILE.exists(),

        "path": str(

            DEFAULT_RISK_FILE,

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
    Risk Engine information.
    """

    return {

        "service": "Risk Engine",

        "input": str(

            DEFAULT_PREDICTION_FILE,

        ),

        "default_output": str(

            DEFAULT_RISK_FILE,

        ),

        "endpoints": [

            "POST /risk",

            "GET /risk/summary",

            "GET /risk/exists",

            "GET /risk/info",

        ],

    }
