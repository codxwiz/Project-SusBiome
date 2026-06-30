"""
============================================================
NASA GPM IMERG Ingestion Pipeline
============================================================

Downloads, parses and catalogs GPM IMERG datasets.

Pipeline

NASA CMR
    ↓
Download
    ↓
NetCDF4
    ↓
Parser
    ↓
Parquet
    ↓
Manifest

============================================================
"""

from __future__ import annotations

import logging

from urllib.parse import urlparse

from pathlib import Path

from typing import Iterable

from scripts.sources.common.downloader import Downloader
from scripts.sources.common.manifest import ManifestCatalog
from scripts.sources.common.storage import Storage

from scripts.sources.nasa.discovery import NASAEarthdataDiscovery
from scripts.sources.nasa.models import Product
from scripts.sources.nasa.gpm.parse_gpm import GPMParser
logger = logging.getLogger(
    "susbiome.gpm.ingest"
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
    BRONZE_ROOT = Path(
    "data/bronze/nasa/gpm"
)

# Manifest status constants
STATUS_PENDING = "pending"
STATUS_PARSED = "parsed"

SILVER_ROOT = Path(
    "data/silver/gpm"
)
class GPMIngestor:
    """
    Production GPM ingestion pipeline.
    """
        # ======================================================
    # INITIALIZE
    # ======================================================

    def __init__(
        self,
        *,
        discovery: NASAEarthdataDiscovery,
        downloader: Downloader,
        storage: Storage,
        manifest: ManifestCatalog,
    ) -> None:

        self.discovery = discovery

        self.downloader = downloader

        self.storage = storage

        self.manifest = manifest

        self.downloaded = 0

        self.parsed = 0

        self.failed = 0

        logger.info(

            "GPM Ingestor initialized."

        )
            # ======================================================
    # DOWNLOAD PATH
    # ======================================================

    def _build_download_path(
        self,
        *,
        granule_id: str,
        file_name: str,
    ) -> Path:
        """
        Return the local Bronze file path for a granule.
        """

        return (

            BRONZE_ROOT

            / granule_id

            / file_name

        )
        # ======================================================
    # PARQUET PATH
    # ======================================================

    def _build_parquet_path(
        self,
        *,
        granule_id: str,
    ) -> Path:
        """
        Return the Silver parquet path.
        """

        return (

            SILVER_ROOT

            / f"{granule_id}.parquet"

        )
        # ======================================================
    # DOWNLOAD
    # ======================================================

    def _download(
        self,
        *,
        granule,
    ) -> Path:
        """
        Download a single GPM granule.

        Returns
        -------
        Path
            Local NetCDF file.
        """

        file_name = Path(

            urlparse(
                granule.url
            ).path

        ).name

        destination = self._build_download_path(

            granule_id=granule.granule_id,

            file_name=file_name,

        )

        if destination.exists():

            logger.info(

                f"Already downloaded: {destination.name}"

            )

            return destination

        self.downloader.download(

            provider="NASA",

            url=granule.url,

            destination=destination,

        )

        self.downloaded += 1

        return destination
        # ======================================================
    # PARSE
    # ======================================================

    def _parse(
        self,
        *,
        granule,
        input_file: Path,
    ) -> Path:
        """
        Parse a downloaded NetCDF file into
        a Silver Parquet dataset.
        """

        output_file = self._build_parquet_path(

            granule_id=granule.granule_id,

        )

        parser = GPMParser(

            input_file=input_file,

            output_file=output_file,

        )

        with parser:

            parser.open_dataset()

            parser.validate()

            parser.extract_metadata()

            parser.extract_coordinates()

            parser.extract_precipitation()

            parser.build_dataframe()

            parser.save_parquet()

        self.parsed += 1

        return output_file
            # ======================================================
    # PROCESS GRANULE
    # ======================================================

    def process_granule(
        self,
        *,
        granule,
    ) -> None:
        """
        Download, parse and register one granule.
        """

        try:
            if not self.manifest.exists(
                granule.granule_id,
            ):
                self.manifest.register(
                    {
                        "dataset_id": granule.granule_id,
                        "provider": granule.product.provider,
                        "product": granule.product.product,
                        "version": granule.product.version,
                        "dataset_type": "granule",
                        "granule_id": granule.granule_id,
                        "coverage_start": granule.start_time,
                        "coverage_end": granule.end_time,
                        "download_time": None,
                        "status": STATUS_PENDING,
                        "source_url": granule.url,
                        "file_name": Path(granule.url).name,
                        "local_path": None,
                        "content_type": granule.content_type,
                        "file_size": granule.size_bytes,
                        "sha256": granule.checksum,
                        "error": None,
                        "metadata": None,
                    }
                )

            input_file = self._download(
                granule=granule,
            )

            self.manifest.mark_downloaded(

                dataset_id=granule.granule_id,

                local_path=str(input_file),

                file_size=granule.size_bytes,

                sha256=granule.checksum,

            )   

            output_file = self._parse(
                granule=granule,
                input_file=input_file,
            )

            self.manifest.mark_parsed(
                dataset_id=granule.granule_id,
                local_path=str(output_file),
            )

        except Exception as exc:
            self.failed += 1
            self.manifest.mark_failed(
                dataset_id=granule.granule_id,
                reason=str(exc),
            )
            logger.exception(
                f"Failed to process {granule.granule_id}"
            )
        # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
        *,
        product: Product,
        start_date,
        end_date,
    ) -> None:
        """
        Execute the ingestion pipeline.
        """

        logger.info(

            "Starting GPM ingestion."

        )

        granules = self.discovery.discover(

            product=product,

            start=start_date,

            end=end_date,

        )

        logger.info(

            f"{len(granules)} granules discovered."

        )

        for granule in granules:

            if self.manifest.is_status(

                dataset_id=granule.granule_id,

                status=STATUS_PARSED,

            ):

                logger.info(

                    f"Skipping already parsed granule: "

                    f"{granule.granule_id}"

                )

                continue

            self.process_granule(

                granule=granule,

            )

        self.summary()
            # ======================================================
    # SUMMARY
    # ======================================================

    def summary(
        self,
    ) -> None:
        """
        Log ingestion summary.
        """

        logger.info("")

        logger.info("=" * 60)

        logger.info("GPM INGESTION SUMMARY")

        logger.info("=" * 60)

        logger.info(

            f"Downloaded : {self.downloaded}"

        )

        logger.info(

            f"Parsed      : {self.parsed}"

        )

        logger.info(

            f"Failed      : {self.failed}"

        )
        if __name__ == "__main__":

            raise SystemExit(

        "Run this module from a pipeline or CLI entry point."

    )