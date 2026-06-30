"""Security, request tracing, and lightweight abuse controls for the API."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

logger = logging.getLogger(__name__)


def _csv_environment(name: str, default: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


class MinuteRateLimiter:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.requests: dict[str, deque[float]] = defaultdict(deque)
        self.lock = asyncio.Lock()

    async def allow(self, key: str, now: float) -> bool:
        async with self.lock:
            values = self.requests[key]
            while values and values[0] <= now - 60:
                values.popleft()
            if len(values) >= self.limit:
                return False
            values.append(now)
            return True


def configure_middleware(app: FastAPI) -> None:
    environment = os.getenv("SUSBIOME_ENV", "development").lower()
    origins = _csv_environment("SUSBIOME_CORS_ORIGINS", "http://localhost:8501")
    hosts = _csv_environment(
        "SUSBIOME_ALLOWED_HOSTS",
        "localhost,127.0.0.1,testserver" if environment != "production" else "",
    )
    if environment == "production" and not hosts:
        raise RuntimeError("SUSBIOME_ALLOWED_HOSTS is required in production.")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts or ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
    )

    maximum_body = int(os.getenv("SUSBIOME_MAX_REQUEST_BYTES", str(1024 * 1024)))
    limiter = MinuteRateLimiter(int(os.getenv("SUSBIOME_RATE_LIMIT_PER_MINUTE", "60")))

    @app.middleware("http")
    async def request_controls(request: Request, call_next):
        started = time.monotonic()
        supplied_request_id = request.headers.get("X-Request-ID", "")
        request_id = supplied_request_id[:64] if supplied_request_id else uuid4().hex
        request.state.request_id = request_id

        content_length = request.headers.get("content-length")
        try:
            body_size = int(content_length) if content_length else 0
        except ValueError:
            body_size = maximum_body + 1
        if body_size > maximum_body:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body is too large.", "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )
        client = request.client.host if request.client else "unknown"
        if request.url.path not in {"/", "/api/health", "/api/health/ready"}:
            if not await limiter.allow(client, time.monotonic()):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded.", "request_id": request_id},
                    headers={"X-Request-ID": request_id, "Retry-After": "60"},
                )
        response = await call_next(request)
        duration_ms = (time.monotonic() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
