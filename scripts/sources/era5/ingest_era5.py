"""
============================================================
ERA5 Ingestion Pipeline
============================================================

Downloads ERA5 datasets from the Copernicus
Climate Data Store (CDS).

Pipeline

CDS
    ↓
Download
    ↓
Bronze Storage
    ↓
Manifest

============================================================
"""

from __future__ import annotations

import logging

from pathlib import Path
from urllib.parse import urlparse

from scripts.sources.era5.parse_era5 import ERA5Parser

from scripts.sources.common.manifest import ManifestCatalog
from scripts.sources.common.storage import Storage

from scripts.sources.era5.client import ERA5Client
from scripts.sources.era5.models import Product

logger = logging.getLogger(
    "susbiome.era5.ingest"
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
    "data/bronze/era5"
)

STATUS_PENDING = "pending"

STATUS_DOWNLOADED = "downloaded"


class ERA5Ingestor:
    """
    Production ERA5 ingestion pipeline.
    """

    # ======================================================
    # INITIALIZE
    # ======================================================

    def __init__(
        self,
        *,
        client: ERA5Client,
        storage: Storage,
        manifest: ManifestCatalog,
    ) -> None:

        self.client = client

        self.storage = storage

        self.manifest = manifest

        self.downloaded = 0

        self.failed = 0

        logger.info(
            "ERA5 Ingestor initialized."
        )

    # ======================================================
    # DOWNLOAD PATH
    # ======================================================

    def _build_download_path(
        self,
        *,
        dataset: str,
        year: int,
        month: int,
    ) -> Path:

        filename = (

            f"{dataset}_"

            f"{year:04d}_"

            f"{month:02d}.nc"

        )

        return (

            BRONZE_ROOT

            / dataset

            / filename

        )

    # ======================================================
    # DOWNLOAD
    # ======================================================

    def download(
        self,
        *,
        product: Product,
        request: dict,
        year: int,
        month: int,
    ) -> Path:

        destination = self._build_download_path(

            dataset=product.dataset,

            year=year,

            month=month,

        )

        if destination.exists():

            logger.info(

                f"Already downloaded: "

                f"{destination.name}"

            )

            return destination

        destination.parent.mkdir(

            parents=True,

            exist_ok=True,

        )

        self.client.download(

            dataset=product.dataset,

            request=request,

            destination=destination,

        )

        self.downloaded += 1
        return destination

    # ======================================================
    # REGISTER
    # ======================================================

    def _register(
        self,
        *,
        product: Product,
        request: dict,
        destination: Path,
    ) -> None:
        """
        Register the download in the manifest.
        """

        dataset_id = destination.stem

        if self.manifest.exists(
            dataset_id,
        ):
            return

        self.manifest.register(

            {

                "dataset_id": dataset_id,

                "provider": product.provider,

                "product": product.dataset,

                "version": "",

                "dataset_type": "monthly",

                "granule_id": dataset_id,

                "coverage_start": None,

                "coverage_end": None,

                "download_time": None,

                "status": STATUS_PENDING,

                "source_url": "CDS",

                "file_name": destination.name,

                "local_path": str(destination),

                "content_type": "application/x-netcdf",

                "file_size": None,

                "sha256": None,

                "error": None,

                "metadata": None,

            }

        )

    # ======================================================
    # PROCESS
    # ======================================================

    def process(
        self,
        *,
        product: Product,
        request: dict,
        variable: str,
        year: int,
        month: int,
    ) -> Path:
        """
        Download, parse and catalog one ERA5 dataset.
        """

        #
        # Download
        #
        input_file = self.download(
            product=product,
            request=request,
            year=year,
            month=month,
        )

        #
        # Register
        #
        self._register(
            product=product,
            request=request,
            destination=input_file,
        )

        #
        # Manifest → DOWNLOADED
        #
        self.manifest.mark_downloaded(
            dataset_id=input_file.stem,
            local_path=str(input_file),
        )

        #
        # Silver output
        #
        output_file = (
            Path("data/silver/era5")
            / f"{input_file.stem}.parquet"
        )

        #
        # Parse
        #
        with ERA5Parser(
            input_file=input_file,
            output_file=output_file,
        ) as parser:
            parser.open_dataset()
            parser.validate()
            parser.extract_metadata()
            parser.extract_coordinates()
            parser.extract_variable(
                variable
            )
            parser.build_dataframe()
            parser.save_parquet()

        #
        # Manifest → PARSED
        #
        self.manifest.mark_parsed(
            dataset_id=input_file.stem,
            local_path=str(output_file),
        )

        return output_file

    # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
        *,
        product,
        request,
        variable: str,
        year,
        month,
    ) -> Path:

        logger.info("")

        logger.info("=" * 60)
        logger.info("STARTING ERA5 INGESTION")
        logger.info("=" * 60)

        try:
            destination = self.process(
                product=product,
                request=request,
                variable=variable,
                year=year,
                month=month,
            )
        except Exception as exc:
            self.failed += 1
            logger.exception("ERA5 ingestion failed.")
            raise exc

        self.summary()
        return destination

    # ======================================================
    # SUMMARY
    # ======================================================

    def summary(
        self,
    ) -> None:

        logger.info("")

        logger.info(

            "=" * 60

        )

        logger.info(

            "ERA5 INGESTION SUMMARY"

        )

        logger.info(

            "=" * 60

        )

        logger.info(

            f"Downloaded : "

            f"{self.downloaded}"

        )

        logger.info(

            f"Failed : "

            f"{self.failed}"

        )

        logger.info(

            "=" * 60

        )

    # ======================================================
    # CONTEXT MANAGER
    # ======================================================

    def __enter__(
        self,
    ) -> "ERA5Ingestor":

        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:

        return None