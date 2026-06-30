"""
============================================================
ERA5 Orchestrator
============================================================

Coordinates ERA5 ingestion.

Workflow

Build Request
      ↓
ERA5 Ingestor
      ↓
Finished

============================================================
"""

from __future__ import annotations

import logging

from scripts.sources.era5.ingest_era5 import ERA5Ingestor
from scripts.sources.era5.models import Product


logger = logging.getLogger(
    "susbiome.era5.orchestrator"
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


class ERA5Orchestrator:
    """
    Coordinates ERA5 ingestion.
    """

    # ======================================================
    # INITIALIZE
    # ======================================================

    def __init__(
        self,
        *,
        ingestor: ERA5Ingestor,
    ) -> None:

        self.ingestor = ingestor

        logger.info(

            "ERA5 Orchestrator initialized."

        )

    # ======================================================
    # BUILD REQUEST
    # ======================================================

    @staticmethod
    def build_request(
        *,
        variable: str,
        year: int,
        month: int,
        day: int,
        hour: str,
    ) -> dict:
        """
        Build a CDS request.
        """

        variable_map = {

            "t2m":

                "2m_temperature",

            "tp":

                "total_precipitation",

            "sp":

                "surface_pressure",

            "u10":

                "10m_u_component_of_wind",

            "v10":

                "10m_v_component_of_wind",

            "d2m":

                "2m_dewpoint_temperature",

        }

        if variable not in variable_map:

            raise ValueError(

                f"Unsupported variable: {variable}"

            )

        return {

            "product_type":

                "reanalysis",

            "variable": [

                variable_map[variable]

            ],

            "year":

                f"{year:04d}",

            "month":

                f"{month:02d}",

            "day":

                f"{day:02d}",

            "time": [

                hour

            ],

            "format":

                "netcdf",

        }

    # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
        *,
        product: Product,
        variable: str,
        year: int,
        month: int,
        day: int,
        hour: str = "12:00",
    ):
        """
        Execute one ERA5 ingestion.
        """

        logger.info(

            "Starting ERA5 orchestration."

        )

        request = self.build_request(

            variable=variable,

            year=year,

            month=month,

            day=day,

            hour=hour,

        )

        return self.ingestor.run(

            product=product,

            request=request,

            variable=variable,

            year=year,

            month=month,

        )