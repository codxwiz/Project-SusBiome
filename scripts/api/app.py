"""
==============================================================
Project SusBiome
API Application
==============================================================

Main FastAPI application.

Responsibilities
----------------
• Create FastAPI application
• Configure metadata
• Initialize shared services
• Register routers
• Configure startup events

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from scripts.api.dependencies import (
    initialize,
)

from scripts.api.models import (
    API_DESCRIPTION,
    API_NAME,
    API_PREFIX,
    API_VERSION,
)
from scripts.api.middleware import configure_middleware

from scripts.api.routers.health import (
    router as health_router,
)

from scripts.api.routers.districts import (
    router as districts_router,
)

from scripts.api.routers.prediction import (
    router as prediction_router,
)

from scripts.api.routers.risk import (
    router as risk_router,
)


# ==========================================================
# LIFESPAN
# ==========================================================

@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """
    Initialize API services.
    """

    initialize()

    yield


# ==========================================================
# APPLICATION
# ==========================================================

app = FastAPI(

    title=API_NAME,

    version=API_VERSION,

    description=API_DESCRIPTION,

    lifespan=lifespan,

)

configure_middleware(app)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, error: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    import logging

    logging.getLogger(__name__).exception("Unhandled API error request_id=%s", request_id)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error.", "request_id": request_id},
    )


# ==========================================================
# ROOT
# ==========================================================

@app.get(
    "/",
    tags=[
        "Root",
    ],
)
def root() -> dict:
    """
    API root endpoint.
    """

    return {

        "service": API_NAME,

        "version": API_VERSION,

        "status": "OK",

        "documentation": "/docs",

        "health": f"{API_PREFIX}/health",

    }


# ==========================================================
# ROUTERS
# ==========================================================

app.include_router(

    health_router,

    prefix=API_PREFIX,

)

app.include_router(

    districts_router,

    prefix=API_PREFIX,

)

app.include_router(

    prediction_router,

    prefix=API_PREFIX,

)

app.include_router(

    risk_router,

    prefix=API_PREFIX,

)


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "scripts.api.app:app",

        host="0.0.0.0",

        port=8000,

        reload=False,

    )
