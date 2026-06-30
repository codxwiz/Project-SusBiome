"""
============================================================
NASA Earthdata Client
============================================================

Purpose
-------
Central HTTP client for NASA services.

Responsibilities

✓ Authenticate using AuthManager

✓ Execute HTTP requests

✓ Return parsed JSON

✓ Handle pagination

✓ Raise NASA-specific exceptions

No product logic.
No discovery logic.
No downloading.

============================================================
"""
from __future__ import annotations

import logging

from typing import Any

import requests

from requests import Response
from requests import Session

from scripts.sources.common.auth import AuthManager

from scripts.sources.common.config import (
    PROVIDER_NASA,
    HTTP_TIMEOUT,
)

from scripts.sources.nasa.exceptions import (
    NASAAuthenticationError,
    NASARequestError,
    NASAResponseError,
)
# ==========================================================
# LOGGER
# ==========================================================

logger = logging.getLogger(
    "susbiome.nasa.client"
)

if not logger.handlers:

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    console = logging.StreamHandler()

    console.setFormatter(formatter)

    logger.addHandler(console)
    # ==========================================================
# NASA CLIENT
# ==========================================================

class NASAClient:
    """
    Production HTTP client for NASA Earthdata.
    """
    def __init__(
        self,
        auth: AuthManager | None = None,
    ) -> None:

        self._auth = auth or AuthManager()

        self._session: Session = self._auth.session(
            PROVIDER_NASA
        )
            # ======================================================
    # REQUEST
    # ======================================================

    def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Response:
        """
        Execute an authenticated HTTP request.
        """

        kwargs.setdefault(
            "timeout",
            HTTP_TIMEOUT,
        )

        try:

            response = self._session.request(
                method=method,
                url=url,
                **kwargs,
            )
            logger.info(

            f"{method} {url}"

        )

        except requests.RequestException as exc:

            raise NASARequestError(
                f"Request failed: {url}"
            ) from exc

        if response.status_code == 401:

            raise NASAAuthenticationError(
                "NASA authentication failed."
            )

        if not response.ok:

            raise NASARequestError(
                f"HTTP {response.status_code}: {url}"
            )

        return response
        # ======================================================
    # GET JSON
    # ======================================================

    def get_json(
        self,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute a GET request and return JSON.
        """

        response = self._request(
            "GET",
            url,
            **kwargs,
        )

        try:

            return response.json()

        except ValueError as exc:

            raise NASAResponseError(
                "NASA returned invalid JSON."
            ) from exc
            # ======================================================
    # GET RESPONSE
    # ======================================================

    def get(
        self,
        url: str,
        **kwargs: Any,
    ) -> Response:
        """
        Execute a GET request.
        """

        return self._request(
            "GET",
            url,
            **kwargs,
        )
        # ======================================================
    # HEAD
    # ======================================================

    def head(
        self,
        url: str,
        **kwargs: Any,
    ) -> Response:
        """
        Execute a HEAD request.
        """

        return self._request(
            "HEAD",
            url,
            **kwargs,
        )
        # ======================================================
    # HEALTH CHECK
    # ======================================================

    def health_check(
        self,
        url: str,
    ) -> bool:
        """
        Verify that a NASA endpoint is reachable.
        """

        try:

            response = self.head(url)

            return response.ok

        except NASARequestError:

            return False
            # ======================================================
    # CLOSE
    # ======================================================

    def close(
        self,
    ) -> None:
        """
        Close the underlying HTTP session.
        """

        self._session.close()

        logger.info(

            "NASA client closed."

        )
            # ======================================================
    # CONTEXT MANAGER
    # ======================================================

    def __enter__(
        self,
    ) -> "NASAClient":

        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:

        self.close()