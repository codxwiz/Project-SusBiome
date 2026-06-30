"""
==============================================================
Project SusBiome
Historical ERA5 Scheduler
==============================================================

Schedules historical ERA5 ingestion.

Pipeline
--------
Date Range
    ↓
Monthly Iterator
    ↓
Request Builder
    ↓
ERA5Ingestor
    ↓
Silver Dataset

This module DOES NOT download ERA5 itself.
It orchestrates the existing production
ERA5Ingestor.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from scripts.ingestion.models import (
    DEFAULT_RANGE,
)

from scripts.sources.era5.ingest_era5 import (
    ERA5Ingestor,
)

from scripts.sources.era5.models import (
    Product,
)

logger = logging.getLogger(__name__)


# ==========================================================
# MONTH
# ==========================================================

@dataclass(slots=True, frozen=True)
class MonthPeriod:

    year: int

    month: int


# ==========================================================
# HISTORICAL ERA5
# ==========================================================

class HistoricalERA5:
    """
    Historical ERA5 scheduler.
    """

    def __init__(
        self,
        *,
        ingestor: ERA5Ingestor,
    ) -> None:

        self.ingestor = ingestor

        self.completed = 0

        self.failed = 0

        logger.info(
            "Historical ERA5 initialized."
        )

    # ======================================================
    # MONTHS
    # ======================================================

    @staticmethod
    def months(
        *,
        start: date,
        end: date,
    ) -> list[MonthPeriod]:
        """
        Generate monthly periods.
        """

        months: list[MonthPeriod] = []

        year = start.year

        month = start.month

        while (year, month) <= (

            end.year,

            end.month,

        ):

            months.append(

                MonthPeriod(

                    year,

                    month,

                )

            )

            month += 1

            if month > 12:

                month = 1

                year += 1

        return months

    # ======================================================
    # REQUEST
    # ======================================================

    @staticmethod
    def build_request(
        *,
        variable: str,
        period: MonthPeriod,
    ) -> dict:
        """
        CDS request.
        """

        last_day = calendar.monthrange(

            period.year,

            period.month,

        )[1]

        return {

            "product_type": [

                "reanalysis",

            ],

            "variable": [

                variable,

            ],

            "year": [

                f"{period.year}",

            ],

            "month": [

                f"{period.month:02d}",

            ],

            "day": [

                f"{d:02d}"

                for d in range(

                    1,

                    last_day + 1,

                )

            ],

            "time": [

                f"{h:02d}:00"

                for h in range(24)

            ],

            "format": "netcdf",

        }

    # ======================================================
    # INGEST
    # ======================================================

    def ingest_month(
        self,
        *,
        product: Product,
        variable: str,
        period: MonthPeriod,
    ) -> Path:
        """
        Ingest one month.
        """

        logger.info(

            "Processing %04d-%02d",

            period.year,

            period.month,

        )

        request = self.build_request(

            variable=variable,

            period=period,

        )

        output = self.ingestor.run(

            product=product,

            request=request,

            variable=variable,

            year=period.year,

            month=period.month,

        )

        self.completed += 1

        return output

    # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
        *,
        product: Product,
        variable: str,
        start: date = DEFAULT_RANGE.start,
        end: date = DEFAULT_RANGE.end,
    ) -> list[Path]:
        """
        Run historical ingestion.
        """

        logger.info("=" * 60)

        logger.info(

            "STARTING HISTORICAL ERA5"

        )

        logger.info("=" * 60)

        outputs: list[Path] = []

        for period in self.months(

            start=start,

            end=end,

        ):

            try:

                result = self.ingest_month(

                    product=product,

                    variable=variable,

                    period=period,

                )

                outputs.append(

                    result,

                )

            except Exception:

                self.failed += 1

                logger.exception(

                    "Failed %04d-%02d",

                    period.year,

                    period.month,

                )

        self.summary()

        return outputs

    # ======================================================
    # SUMMARY
    # ======================================================

    def summary(
        self,
    ) -> None:

        logger.info("")

        logger.info("=" * 60)

        logger.info(

            "HISTORICAL ERA5 SUMMARY"

        )

        logger.info("=" * 60)

        logger.info(

            "Completed : %d",

            self.completed,

        )

        logger.info(

            "Failed    : %d",

            self.failed,

        )

        logger.info("=" * 60)