"""
==============================================================
Project SusBiome
API Models
==============================================================

Shared API models and constants.

Responsibilities
----------------
• API response schemas
• API metadata
• Route constants
• Default paths

This module intentionally contains NO API routes.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sources.common.config import PROJECT_ROOT


# ==========================================================
# API
# ==========================================================

API_NAME = "Project SusBiome API"

API_VERSION = "1.3.0"

API_DESCRIPTION = (

    "Flood, drought, and cyclone weather and physical land susceptibility API."

)


# ==========================================================
# ROUTES
# ==========================================================

API_PREFIX = "/api"

HEALTH_ROUTE = "/health"

PREDICTION_ROUTE = "/prediction"

RISK_ROUTE = "/risk"


# ==========================================================
# DATA
# ==========================================================

DATA_DIRECTORY = PROJECT_ROOT / "data"

PREDICTION_DIRECTORY = (

    DATA_DIRECTORY

    / "prediction"

)

RISK_DIRECTORY = (

    DATA_DIRECTORY

    / "risk"

)


DEFAULT_PREDICTION_FILE = (

    PREDICTION_DIRECTORY

    / "predictions.parquet"

)


DEFAULT_RISK_FILE = (

    RISK_DIRECTORY

    / "risk.parquet"

)

DEFAULT_FEATURE_FILE = DATA_DIRECTORY / "serving" / "current_features.parquet"


def resolve_data_path(
    value: str | Path | None,
    *,
    default: Path,
    output: bool = False,
) -> Path:
    """Resolve API paths while preventing access outside the data directory."""
    candidate = Path(value) if value is not None else default
    if not candidate.is_absolute():
        candidate = (
            PROJECT_ROOT / candidate
            if candidate.parts and candidate.parts[0] == "data"
            else DATA_DIRECTORY / candidate
        )
    candidate = candidate.resolve()
    try:
        candidate.relative_to(DATA_DIRECTORY.resolve())
    except ValueError as error:
        raise ValueError("API paths must remain inside the data directory.") from error
    if candidate.suffix.lower() not in {".parquet", ".csv"}:
        raise ValueError("Only Parquet and CSV datasets are supported.")
    if output and candidate == DATA_DIRECTORY.resolve():
        raise ValueError("Output must be a file path.")
    return candidate


# ==========================================================
# STATUS
# ==========================================================

STATUS_OK = "OK"

STATUS_ERROR = "ERROR"


# ==========================================================
# RESPONSE MODELS
# ==========================================================

@dataclass(slots=True, frozen=True)
class HealthResponse:
    """
    API health.
    """

    status: str

    version: str

    service: str


@dataclass(slots=True, frozen=True)
class PredictionResponse:
    """
    Prediction response.
    """

    rows: int

    output: str


@dataclass(slots=True, frozen=True)
class RiskResponse:
    """
    Risk response.
    """

    rows: int

    output: str


# ==========================================================
# DEFAULTS
# ==========================================================

DEFAULT_HEALTH = HealthResponse(

    status=STATUS_OK,

    version=API_VERSION,

    service=API_NAME,

)


# ==========================================================
# EXPORTS
# ==========================================================

__all__ = [

    "API_NAME",

    "API_VERSION",

    "API_DESCRIPTION",

    "API_PREFIX",

    "HEALTH_ROUTE",

    "PREDICTION_ROUTE",

    "RISK_ROUTE",

    "DATA_DIRECTORY",

    "PREDICTION_DIRECTORY",

    "RISK_DIRECTORY",

    "DEFAULT_PREDICTION_FILE",

    "DEFAULT_RISK_FILE",

    "DEFAULT_FEATURE_FILE",

    "resolve_data_path",

    "STATUS_OK",

    "STATUS_ERROR",

    "HealthResponse",

    "PredictionResponse",

    "RiskResponse",

    "DEFAULT_HEALTH",

]
