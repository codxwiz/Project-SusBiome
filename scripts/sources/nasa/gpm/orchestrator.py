"""
============================================================
NASA GPM Daily Orchestrator
============================================================

Coordinates daily ingestion of GPM IMERG datasets.

Workflow

Date Range
    ↓
Daily Discovery
    ↓
Daily Ingestion
    ↓
Manifest
    ↓
Summary

============================================================
"""

from __future__ import annotations

import logging

from datetime import datetime
from datetime import timedelta

from scripts.sources.nasa.models import Product
from scripts.sources.nasa.gpm.ingest_gpm import GPMIngestor

logger = logging.getLogger(
    "susbiome.gpm.orchestrator"
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
        console)


class GPMDailyOrchestrator:
    """
    Execute GPM ingestion over
    a continuous date range.
    """

    # ======================================================
    # INITIALIZE
    # ======================================================

    def __init__(
        self,
        *,
        ingestor: GPMIngestor,
    ) -> None:

        self.ingestor = ingestor

        self.days_total = 0

        self.days_completed = 0

        self.days_failed = 0

        self.start_time: datetime | None = None

        self.end_time: datetime | None = None

        logger.info(
            "GPM Daily Orchestrator initialized."
        )

    # ======================================================
    # GENERATE DATES
    # ======================================================

    @staticmethod
    def _generate_dates(
        *,
        start_date: datetime,
        end_date: datetime,
    ):

        current = start_date

        while current <= end_date:

            yield current

            current += timedelta(
                days=1
            )

    # ======================================================
    # RUN SINGLE DAY
    # ======================================================

    def _run_day(
        self,
        *,
        product: Product,
        date: datetime,
    ) -> None:

        logger.info(

            "------------------------------------------------"

        )

        logger.info(

            f"Processing "

            f"{date.strftime('%Y-%m-%d')}"

        )

        logger.info(

            "------------------------------------------------"

        )

        self.ingestor.run(

            product=product,

            start_date=date,

            end_date=date,

        )

        self.days_completed += 1

    # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
        *,
        product: Product,
        start_date: datetime,
        end_date: datetime,
    ) -> None:

        logger.info("")

        logger.info(
            "=" * 60
        )

        logger.info(
            "STARTING GPM DAILY ORCHESTRATION"
        )

        logger.info(
            "=" * 60
        )

        self.start_time = datetime.now()

        dates = list(

            self._generate_dates(

                start_date=start_date,

                end_date=end_date,

            )

        )

        self.days_total = len(
            dates
        )

        logger.info(

            f"Days to process : "

            f"{self.days_total}"

        )

        logger.info(

            f"Start Date : "

            f"{start_date.date()}"

        )

        logger.info(

            f"End Date : "

            f"{end_date.date()}"

        )

        logger.info("")
        for index, date in enumerate(
            dates,
            start=1,
        ):

            logger.info(

                ""

            )

            logger.info(

                f"[{index}/{self.days_total}] "

                f"{date.strftime('%Y-%m-%d')}"

            )

            try:

                self._run_day(

                    product=product,

                    date=date,

                )

            except Exception:

                self.days_failed += 1

                logger.exception(

                    f"Failed processing "

                    f"{date.strftime('%Y-%m-%d')}"

                )

                #
                # Continue with the
                # remaining dates.
                #
                continue

        self.end_time = datetime.now()

        self.summary()

    # ======================================================
    # SUMMARY
    # ======================================================

    def summary(
        self,
    ) -> None:

        elapsed = None

        if (

            self.start_time is not None

            and

            self.end_time is not None

        ):

            elapsed = (

                self.end_time

                -

                self.start_time

            ).total_seconds()

        logger.info("")

        logger.info(

            "=" * 60

        )

        logger.info(

            "GPM DAILY ORCHESTRATION SUMMARY"

        )

        logger.info(

            "=" * 60

        )

        logger.info(

            f"Days Requested : "

            f"{self.days_total}"

        )

        logger.info(

            f"Completed : "

            f"{self.days_completed}"

        )

        logger.info(

            f"Failed : "

            f"{self.days_failed}"

        )

        logger.info(

            ""

        )

        logger.info(

            "INGESTION TOTALS"

        )

        logger.info(

            f"Downloaded : "

            f"{self.ingestor.downloaded}"

        )

        logger.info(

            f"Parsed : "

            f"{self.ingestor.parsed}"

        )

        logger.info(

            f"Failed : "

            f"{self.ingestor.failed}"

        )

        if elapsed is not None:

            logger.info(

                f"Elapsed : "

                f"{elapsed:.2f} seconds"

            )

        logger.info(

            "=" * 60

        )

    # ======================================================
    # RESET COUNTERS
    # ======================================================

    def reset(
        self,
    ) -> None:

        self.days_total = 0

        self.days_completed = 0

        self.days_failed = 0

        self.start_time = None

        self.end_time = None

    # ======================================================
    # CONTEXT MANAGER
    # ======================================================

    def __enter__(
        self,
    ) -> "GPMDailyOrchestrator":

        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:

        return None

    # ======================================================
    # REPR
    # ======================================================

    def __repr__(
        self,
    ) -> str:

        return (

            "GPMDailyOrchestrator("

            f"days={self.days_total}, "

            f"completed={self.days_completed}, "

            f"failed={self.days_failed})"

        )