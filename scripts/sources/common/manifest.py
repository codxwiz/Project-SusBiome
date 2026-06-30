"""
============================================================
SusBiome Manifest Catalog
============================================================

Purpose
-------
Central metadata catalog for every dataset downloaded into
SusBiome.

This module is provider-agnostic.

Supported providers include:

- NASA
- IMD
- GDELT
- CWC
- NDMA

Every ingestion module MUST register datasets here.

============================================================
"""
from __future__ import annotations

import logging

from datetime import UTC
from datetime import datetime

from pathlib import Path

from typing import Optional

from typing import Any

import pandas as pd

import pyarrow as pa

import pyarrow.parquet as pq
# ==========================================================
# LOGGER
# ==========================================================

logger = logging.getLogger(

    "susbiome.manifest"

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
# DATASET STATUS
# ==========================================================

STATUS_PENDING = "PENDING"

STATUS_DOWNLOADING = "DOWNLOADING"

STATUS_DOWNLOADED = "DOWNLOADED"

STATUS_VALIDATED = "VALIDATED"

STATUS_PARSED = "PARSED"

STATUS_FAILED = "FAILED"
# ==========================================================
# MANIFEST SCHEMA
# ==========================================================

MANIFEST_COLUMNS = [

    "dataset_id",

    "provider",

    "product",

    "version",

    "dataset_type",

    "granule_id",

    "coverage_start",

    "coverage_end",

    "download_time",

    "status",

    "source_url",

    "file_name",

    "local_path",

    "content_type",

    "file_size",

    "sha256",

    "error",

    "metadata",

]
# ==========================================================
# MANIFEST CATALOG
# ==========================================================

class ManifestCatalog:

    """
    Central metadata catalog for SusBiome.
    """

    def __init__(

        self,

        manifest_path: Path,

    ):

        self.manifest_path = Path(

            manifest_path

        )

        self._df = self._load()
            # ======================================================
    # CREATE EMPTY MANIFEST
    # ======================================================

    def _empty_dataframe(
        self,
    ) -> pd.DataFrame:

        """
        Create an empty manifest using the
        SusBiome schema.
        """

        return pd.DataFrame(
            columns=MANIFEST_COLUMNS
        )
        # ======================================================
    # VALIDATE SCHEMA
    # ======================================================

    def _validate_schema(
        self,
        df: pd.DataFrame,
    ) -> None:

        """
        Ensure every required column exists.
        """

        missing = [

            column

            for column in MANIFEST_COLUMNS

            if column not in df.columns

        ]

        if missing:

            raise ValueError(

                "Manifest missing columns: "

                + ", ".join(missing)

            )
            # ======================================================
    # LOAD MANIFEST
    # ======================================================

    def _load(
        self,
    ) -> pd.DataFrame:

        """
        Load an existing manifest.

        If none exists,
        create an empty one.
        """

        if not self.manifest_path.exists():

            logger.info(

                "Manifest not found."

            )

            return self._empty_dataframe()

        df = pd.read_parquet(

            self.manifest_path

        )

        self._validate_schema(

            df

        )

        logger.info(

            f"Loaded "

            f"{len(df):,} "

            f"manifest records."

        )

        return df
        # ======================================================
    # SAVE MANIFEST
    # ======================================================

    def _save(
        self,
    ) -> None:

        """
        Persist manifest to disk.
        """

        self.manifest_path.parent.mkdir(

            parents=True,

            exist_ok=True,

        )

        table = pa.Table.from_pandas(

            self._df,

            preserve_index=False,

        )

        pq.write_table(

            table,

            self.manifest_path,

            compression="snappy",

        )

        logger.info(

            f"Manifest saved: "

            f"{self.manifest_path}"

        )
            # ==========================================================
    # EXISTS
    # ==========================================================

    def exists(
        self,
        dataset_id: str,
    ) -> bool:
        """
        Return True if a dataset already exists
        in the manifest.
        """

        if self._df.empty:

            return False

        return dataset_id in set(

            self._df["dataset_id"]

        )
        # ==========================================================
    # FIND
    # ==========================================================

    def find(
        self,
        dataset_id: str,
    ) -> pd.Series | None:
        """
        Return one manifest row.
        """

        rows = self._df.loc[
            self._df["dataset_id"] == dataset_id
        ]

        if rows.empty:

            return None

        return rows.iloc[0]
            # ==========================================================
    # REGISTER
    # ==========================================================

    def register(
        self,
        record: dict[str, Any],
    ) -> bool:
        """
        Register a dataset.

        Returns
        -------
        True
            Dataset successfully registered.

        False
            Dataset already exists.
        """
                #
        # Validate schema
        #
        missing = [

            column

            for column in MANIFEST_COLUMNS

            if column not in record

        ]

        if missing:

            raise ValueError(

                "Missing manifest fields: "

                + ", ".join(missing)

            )

        dataset_id = record["dataset_id"]

        #
        # Duplicate check
        #
        if self.exists(dataset_id):

            logger.info(

                f"Dataset already exists: "

                f"{dataset_id}"

            )

            return False

        #
        # Append new row
        #
        row = pd.DataFrame(

            [record],

            columns=MANIFEST_COLUMNS,

        )

        self._df = pd.concat(

            [

                self._df,

                row,

            ],

            ignore_index=True,

        )

        self._save()

        logger.info(

            f"Registered dataset "

            f"{dataset_id}"

        )

        return True

    # ==========================================================
    # UPDATE STATUS
    # ==========================================================

    def update_status(
        self,
        dataset_id: str,
        status: str,
        **updates: Any,
    ) -> None:
        """
        Update the dataset status and any additional
        manifest fields in a single operation.
        """

        valid_status = {
            STATUS_PENDING,
            STATUS_DOWNLOADING,
            STATUS_DOWNLOADED,
            STATUS_VALIDATED,
            STATUS_PARSED,
            STATUS_FAILED,
        }

        if status not in valid_status:
            raise ValueError(
                f"unknown status: {status}"
            )

        rows = self._df.index[
            self._df["dataset_id"] == dataset_id
        ]
        if len(rows) == 0:
            raise KeyError(
                f"Dataset not found: "
                f"{dataset_id}"
            )

        row = rows[0]
        self._df.at[row, "status"] = status
        for column, value in updates.items():

            if value is None:

                continue

            if column not in MANIFEST_COLUMNS:

                raise ValueError(

            f"Unknown manifest column: {column}"

        )

        self._df.at[row, column] = value
        self._save()

        logger.info(

            "Manifest updated: "

            f"{dataset_id} -> {status}"

    )   
                # ==========================================================
    # MARK DOWNLOADED
    # ==========================================================

    def mark_downloaded(
    self,
    *,
    dataset_id: str,
    local_path: str,
    file_size: int | None = None,
    sha256: str |None = None,
) -> None:

     self.update_status(

        dataset_id=dataset_id,

        status=STATUS_DOWNLOADED,

        local_path=local_path,

        file_size=file_size,

        sha256=sha256,

    )
                # ==========================================================
    # MARK VALIDATED
    # ==========================================================

    def mark_validated(
    self,
    *,
    dataset_id: str,
) -> None:

     self.update_status(

        dataset_id=dataset_id,

        status=STATUS_VALIDATED,

    )
            # ==========================================================
    # MARK PARSED
    # ==========================================================

    def mark_parsed(
        self,
        *,
        dataset_id: str,
        local_path: str | None = None,
    ) -> None:
        updates = {}
        if local_path is not None:
            updates["local_path"] = local_path
        self.update_status(
            dataset_id=dataset_id,
            status=STATUS_PARSED,
            **updates,
        )
                # ==========================================================
    # MARK FAILED
    # ==========================================================

    def mark_failed(
    self,
    *,
    dataset_id: str,
    reason: str,
) -> None:

     self.update_status(

        dataset_id=dataset_id,

        status=STATUS_FAILED,

        error=reason,

    )
         # ==========================================================
    # STATUS QUERY
    # ==========================================================

    def is_status(
        self,
        *,
        dataset_id: str,
        status: str,
    ) -> bool:
        """
        Return True if a dataset currently has
        the requested status.
        """

        rows = self._df.loc[
            self._df["dataset_id"] == dataset_id
        ]

        if rows.empty:

            return False

        return (

            rows.iloc[0]["status"]

            == status

        )

    # ======================================================
    # FAILED DATASETS
    # ======================================================

    def failed(
        self,
    ) -> pd.DataFrame:
        """
        Return all failed datasets.
        """

        return self._df[
            self._df["status"] == STATUS_FAILED
        ].copy()
        # ======================================================
    # MANIFEST SUMMARY
    # ======================================================

    def summary(
        self,
    ) -> dict:
        """
        Return summary statistics.
        """

        return {

            "datasets": int(

                len(self._df)

            ),

            "providers": int(

                self._df["provider"].nunique()

            ),

            "products": int(

                self._df["product"].nunique()

            ),

            "downloaded": int(

                (self._df["status"] == STATUS_DOWNLOADED).sum()

            ),

            "validated": int(

                (self._df["status"] == STATUS_VALIDATED).sum()

            ),

            "parsed": int(

                (self._df["status"] == STATUS_PARSED).sum()

            ),

            "failed": int(

                (self._df["status"] == STATUS_FAILED).sum()

            ),

        }
        # ======================================================
    # EXPORT DATAFRAME
    # ======================================================

    def to_dataframe(
        self,
    ) -> pd.DataFrame:
        """
        Return a copy of the manifest.
        """

        return self._df.copy()
        # ======================================================
    # NUMBER OF DATASETS
    # ======================================================

    def __len__(
        self,
    ) -> int:

        return len(

            self._df

        )
        # ======================================================
    # STRING REPRESENTATION
    # ======================================================

    def __repr__(
        self,
    ) -> str:

        return (

            f"ManifestCatalog("

            f"datasets={len(self._df)})"

        )
        # ======================================================
    # FIND DUPLICATE DATASETS
    # ======================================================

    def duplicates(
        self,
    ) -> pd.DataFrame:

        """
        Return duplicated scientific datasets.
        """

        keys = [

            "provider",

            "product",

            "version",

            "granule_id",

        ]

        dup = self._df.duplicated(

            subset=keys,

            keep=False,

        )

        return self._df[dup].copy()
        # ======================================================
    # PROVIDER STATISTICS
    # ======================================================

    def provider_summary(
        self,
    ) -> pd.DataFrame:

        return (

            self._df

            .groupby(

                "provider"

            )

            .agg(

                datasets=(

                    "dataset_id",

                    "count",

                ),

                products=(

                    "product",

                    "nunique",

                ),

            )

            .sort_index()

        )
        # ======================================================
    # PRODUCT STATISTICS
    # ======================================================

    def product_summary(
        self,
    ) -> pd.DataFrame:

        return (

            self._df

            .groupby(

                [

                    "provider",

                    "product"

                ]

            )

            .size()

            .reset_index(

                name="datasets"

            )

        )
        # ======================================================
    # MANIFEST INTEGRITY
    # ======================================================

    def validate(
        self,
    ) -> None:

        """
        Validate manifest integrity.
        """

        self._validate_schema(

            self._df

        )

        duplicate_rows = self.duplicates()

        if not duplicate_rows.empty:

            raise ValueError(

                "Duplicate datasets detected."

            )

        logger.info(

            "Manifest integrity OK."

        )
            # ======================================================
    # RELOAD MANIFEST
    # ======================================================

    def reload(
        self,
    ) -> None:

        self._df = self._load()
            # ======================================================
    # CLEAR MANIFEST
    # ======================================================

    def clear(
        self,
    ) -> None:

        self._df = self._empty_dataframe()

        self._save()

        logger.warning(

            "Manifest cleared."

        )