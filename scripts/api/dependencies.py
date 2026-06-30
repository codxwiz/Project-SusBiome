"""
==============================================================
Project SusBiome
API Dependencies
==============================================================

Shared dependencies used across the API.

Responsibilities
----------------
• Create shared Prediction Orchestrator
• Create shared Risk Orchestrator
• Configure logging
• Provide reusable dependency functions

This module contains NO API routes.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging
import hmac
import os

from fastapi import Header, HTTPException

from scripts.prediction.orchestrator import (
    PredictionOrchestrator,
)

from scripts.risk.orchestrator import (
    RiskOrchestrator,
)

logger = logging.getLogger(__name__)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Protect expensive write endpoints when an API key is configured."""
    expected = os.getenv("SUSBIOME_API_KEY")
    environment = os.getenv("SUSBIOME_ENV", "development").lower()
    if environment == "production" and not expected:
        raise HTTPException(status_code=503, detail="SUSBIOME_API_KEY is not configured.")
    if expected and (x_api_key is None or not hmac.compare_digest(x_api_key, expected)):
        raise HTTPException(status_code=401, detail="Invalid API key.")


# ==========================================================
# SINGLETONS
# ==========================================================

_prediction: PredictionOrchestrator | None = None

_risk: RiskOrchestrator | None = None

_errors: dict[str, str] = {}


# ==========================================================
# LOGGER
# ==========================================================

def configure_logging() -> None:
    """
    Configure API logging.

    Safe to call multiple times.
    """

    if logging.getLogger().handlers:
        return

    logging.basicConfig(

        level=logging.INFO,

        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),

    )

    logger.info(
        "Logging configured."
    )


# ==========================================================
# PREDICTION
# ==========================================================

def get_prediction_orchestrator(
) -> PredictionOrchestrator:
    """
    Return shared Prediction Orchestrator.
    """

    global _prediction

    if _prediction is None:

        logger.info(
            "Creating Prediction Orchestrator."
        )

        try:
            _prediction = PredictionOrchestrator()
            _errors.pop("prediction", None)
        except Exception as error:
            _errors["prediction"] = str(error)
            logger.exception("Prediction service initialization failed.")
            raise HTTPException(status_code=503, detail=str(error)) from error

    return _prediction


# ==========================================================
# RISK
# ==========================================================

def get_risk_orchestrator(
) -> RiskOrchestrator:
    """
    Return shared Risk Orchestrator.
    """

    global _risk

    if _risk is None:

        logger.info(
            "Creating Risk Orchestrator."
        )

        try:
            _risk = RiskOrchestrator()
            _errors.pop("risk", None)
        except Exception as error:
            _errors["risk"] = str(error)
            logger.exception("Risk service initialization failed.")
            raise HTTPException(status_code=503, detail=str(error)) from error

    return _risk


# ==========================================================
# RESET
# ==========================================================

def reset_dependencies() -> None:
    """
    Reset cached dependencies.

    Useful for testing.
    """

    global _prediction

    global _risk

    _prediction = None

    _risk = None

    _errors.clear()

    logger.info(
        "API dependencies reset."
    )


# ==========================================================
# STATUS
# ==========================================================

def dependency_status(
) -> dict[str, bool]:
    """
    Dependency status.
    """

    return {

        "prediction":

            _prediction is not None,

        "risk":

            _risk is not None,

    }


def dependency_errors() -> dict[str, str]:
    return _errors.copy()


# ==========================================================
# READY
# ==========================================================

def ready() -> bool:
    """
    Check API readiness.
    """

    return all(

        dependency_status().values()

    )


# ==========================================================
# INITIALIZE
# ==========================================================

def initialize() -> None:
    """
    Initialize shared services.
    """

    configure_logging()

    for initializer in (get_prediction_orchestrator, get_risk_orchestrator):
        try:
            initializer()
        except HTTPException:
            pass

    logger.info(
        "API initialized."
    )
