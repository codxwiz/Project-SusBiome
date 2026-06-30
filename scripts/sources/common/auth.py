"""
============================================================
SusBiome Authentication Manager
============================================================

Purpose
-------
Central authentication manager for all external providers.

Responsibilities

✓ Build authenticated HTTP sessions

✓ Read credentials from configuration

✓ Keep authentication separate from ingestion

No download logic.
No provider business logic.

============================================================
"""
from __future__ import annotations

import logging

import requests

from requests import Session

from scripts.sources.common.config import (

    EARTHDATA_TOKEN,

    IMD_API_KEY,

    PROVIDER_NASA,

    PROVIDER_IMD,

)
# ==========================================================
# LOGGER
# ==========================================================

logger = logging.getLogger(

    "susbiome.auth"

)

if not logger.handlers:

    logger.setLevel(

        logging.INFO

    )

    formatter = logging.Formatter(

        "%(asctime)s | %(levelname)s | %(message)s"

    )

    console = logging.StreamHandler()

    console.setFormatter(

        formatter

    )

    logger.addHandler(

        console

    )
    # ==========================================================
# AUTHENTICATION
# ==========================================================

class AuthManager:

    """
    Central authentication manager.

    One authenticated HTTP session
    per provider.
    """
    def __init__(

        self,

    ):

        self._sessions = {}
            # ======================================================
    # PROVIDER
    # ======================================================

    @staticmethod

    def _validate_provider(

        provider: str,

    ) -> None:

        supported = {

            PROVIDER_NASA,

            PROVIDER_IMD,

        }

        if provider not in supported:

            raise ValueError(

                f"Unsupported provider: {provider}"

            )
            # ======================================================
    # NASA SESSION
    # ======================================================

    def _build_nasa_session(
        self,
    ) -> Session:
        """
        Build an authenticated NASA Earthdata session.
        """

        if not EARTHDATA_TOKEN:

            raise RuntimeError(

                "EARTHDATA_TOKEN environment variable is not set."

            )

        session = requests.Session()

        session.headers.update({

            "Authorization": f"Bearer {EARTHDATA_TOKEN}",

        })

        logger.info(

            "NASA session initialized."

        )

        return session
        # ======================================================
    # GET NASA SESSION
    # ======================================================

    def _nasa_session(
        self,
    ) -> Session:
        """
        Return a cached NASA session.
        """

        if PROVIDER_NASA not in self._sessions:

            self._sessions[PROVIDER_NASA] = (

                self._build_nasa_session()

            )

        return self._sessions[PROVIDER_NASA]
        # ======================================================
    # SESSION
    # ======================================================

    def session(
        self,
        provider: str,
    ) -> Session:
        """
        Return an authenticated session for a provider.
        """

        self._validate_provider(

            provider

        )

        if provider == PROVIDER_NASA:

            return self._nasa_session()

        raise NotImplementedError(

            f"No authentication implemented for {provider}"

        )
        # ======================================================
    # AUTHENTICATED
    # ======================================================

    def authenticated(
        self,
        provider: str,
    ) -> bool:
        """
        Check whether authentication credentials
        are available for a provider.
        """

        self._validate_provider(

            provider

        )

        if provider == PROVIDER_NASA:

            return bool(EARTHDATA_TOKEN)

        if provider == PROVIDER_IMD:

            return bool(IMD_API_KEY)

        return False
        # ======================================================
    # IMD SESSION
    # ======================================================

    def _build_imd_session(
        self,
    ) -> Session:
        """
        Build an authenticated IMD session.
        """

        if not IMD_API_KEY:

            raise RuntimeError(

                "IMD_API_KEY environment variable is not set."

            )

        session = requests.Session()

        session.headers.update({

            "X-API-Key": IMD_API_KEY,

        })

        logger.info(

            "IMD session initialized."

        )

        return session
        # ======================================================
    # GET IMD SESSION
    # ======================================================

    def _imd_session(
        self,
    ) -> Session:

        if PROVIDER_IMD not in self._sessions:

            self._sessions[PROVIDER_IMD] = (

                self._build_imd_session()

            )

        return self._sessions[PROVIDER_IMD]
        # ======================================================
    # SESSION
    # ======================================================

    def session(
        self,
        provider: str,
    ) -> Session:

        self._validate_provider(

            provider

        )

        if provider == PROVIDER_NASA:

            return self._nasa_session()

        if provider == PROVIDER_IMD:

            return self._imd_session()

        raise NotImplementedError(

            provider

        )
        # ======================================================
    # RESET SESSION
    # ======================================================

    def reset(
        self,
        provider: str,
    ) -> None:

        self._validate_provider(

            provider

        )

        self._sessions.pop(

            provider,

            None,

        )

        logger.info(

            f"Reset session: {provider}"

        )
            # ======================================================
    # VALIDATE CREDENTIALS
    # ======================================================

    def validate(
        self,
        provider: str,
    ) -> None:

        self._validate_provider(

            provider

        )

        if provider == PROVIDER_NASA:

            if not EARTHDATA_TOKEN:

                raise RuntimeError(

                    "Missing EARTHDATA_TOKEN"

                )

        if provider == PROVIDER_IMD:

            if not IMD_API_KEY:

                raise RuntimeError(

                    "Missing IMD_API_KEY"

                )
                # ======================================================
    # CLOSE
    # ======================================================

    def close(
        self,
    ) -> None:

        for session in self._sessions.values():

            session.close()

        self._sessions.clear()

        logger.info(

            "All sessions closed."

        )