"""
============================================================
ERA5 CDS Client
============================================================

Production client for downloading ERA5 datasets
from the Copernicus Climate Data Store (CDS).

Responsibilities
----------------
- Connect to CDS
- Download datasets
- Verify client health

============================================================
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cdsapi

logger = logging.getLogger(
    "susbiome.era5.client"
)

if not logger.handlers:

    logger.setLevel(
        logging.INFO
    )

    console = logging.StreamHandler()

    console.setFormatter(

        logging.Formatter(

            "%(asctime)s | %(levelname)s | %(message)s"

        )

    )

    logger.addHandler(
        console
    )


class ERA5Client:
    """
    Production CDS API client.
    """

    # ======================================================
    # INITIALIZE
    # ======================================================

    def __init__(
        self,
        *,
        quiet: bool = False,
        verify: bool = True,
    ) -> None:

        self.client = cdsapi.Client(

            quiet=quiet,

            verify=verify,

        )

        logger.info(

            "ERA5 client initialized."

        )

    # ======================================================
    # HEALTH CHECK
    # ======================================================

    def health_check(
        self,
    ) -> bool:
        """
        Verify CDS client is available.
        """

        try:

            return self.client is not None

        except Exception:

            return False

    # ======================================================
    # DOWNLOAD
    # ======================================================

    def download(
        self,
        *,
        dataset: str,
        request: dict[str, Any],
        destination: Path,
    ) -> Path:
        """
        Download one ERA5 dataset.
        """

        destination.parent.mkdir(

            parents=True,

            exist_ok=True,

        )

        logger.info(

            f"Dataset : {dataset}"

        )

        logger.info(

            f"Destination : {destination}"

        )

        self.client.retrieve(

            name=dataset,

            request=request,

            target=str(destination),

        )

        logger.info(

            "Download completed."

        )

        return destination

    # ======================================================
    # CONTEXT MANAGER
    # ======================================================

    def __enter__(
        self,
    ) -> "ERA5Client":

        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:

        return None