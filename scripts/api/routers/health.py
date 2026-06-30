"""
==============================================================
Project SusBiome
Health Router
==============================================================

Health endpoint for the Project SusBiome API.

Responsibilities
----------------
• API health check
• Dependency status
• Service readiness
• Version information

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from scripts.api.dependencies import (
    dependency_status,
    dependency_errors,
    ready,
)

from scripts.api.models import (
    API_NAME,
    API_VERSION,
)

router = APIRouter(

    prefix="/health",

    tags=[

        "Health",

    ],

)


# ==========================================================
# ROOT
# ==========================================================

@router.get(
    "",
)
def health() -> dict:
    """
    Health endpoint.
    """

    return {

        "status": "OK",

        "service": API_NAME,

        "version": API_VERSION,

    }


# ==========================================================
# READY
# ==========================================================

@router.get(
    "/ready",
)
def readiness(response: Response) -> dict:
    """
    API readiness.
    """

    is_ready = ready()
    if not is_ready:
        response.status_code = HTTP_503_SERVICE_UNAVAILABLE
    return {

        "ready": is_ready,

        "dependencies": dependency_status(),

        "errors": dependency_errors(),

    }


# ==========================================================
# VERSION
# ==========================================================

@router.get(
    "/version",
)
def version() -> dict:
    """
    API version.
    """

    return {

        "service": API_NAME,

        "version": API_VERSION,

    }


# ==========================================================
# STATUS
# ==========================================================

@router.get(
    "/status",
)
def status() -> dict:
    """
    Complete health status.
    """

    return {

        "status": "OK",

        "service": API_NAME,

        "version": API_VERSION,

        "ready": ready(),

        "dependencies": dependency_status(),

        "errors": dependency_errors(),

    }
