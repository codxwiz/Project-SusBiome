"""
============================================================
SusBiome Storage Manager
============================================================

Purpose
-------
Central filesystem manager for SusBiome.

Every ingestion module must use this module.

Responsibilities

✓ Create directories

✓ Build file paths

✓ Save files

✓ Read files

✓ Delete files

✓ List files

No ingestion module should directly manipulate the
filesystem.

============================================================
"""

from __future__ import annotations
import uuid
import shutil
import logging

from pathlib import Path

from typing import Iterable
from typing import Optional
logger = logging.getLogger(

    "susbiome.storage"

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
# STORAGE
# ==========================================================

class Storage:

    """
    Central filesystem manager.
    """
    def __init__(

        self,

        root: Path,

    ):

        self.root = Path(

            root

        )

        self._initialize()
            # ======================================================
    # INITIALIZE
    # ======================================================

    def _initialize(

        self,

    ) -> None:

        directories = [

            self.root / "bronze",

            self.root / "silver",

            self.root / "gold",

            self.root / "logs",

            self.root / "metadata",

            self.root / "temp",

        ]

        for directory in directories:

            directory.mkdir(

                parents=True,

                exist_ok=True,

            )

        logger.info(

            "Storage initialized."

        )
            # ======================================================
    # BUILD DIRECTORY
    # ======================================================

    def _directory(
        self,
        layer: str,
        provider: str,
        product: str,
    ) -> Path:
        """
        Return the directory for a provider/product
        within the requested storage layer.
        """

        path = (

            self.root
            / layer
            / provider.lower()
            / product.lower()

        )

        path.mkdir(

            parents=True,
            exist_ok=True,

        )

        return path
        # ======================================================
    # BRONZE PATH
    # ======================================================

    def raw_path(
        self,
        provider: str,
        product: str,
    ) -> Path:

        return self._directory(

            "bronze",

            provider,

            product,

        )
        # ======================================================
    # SILVER PATH
    # ======================================================

    def silver_path(
        self,
        provider: str,
        product: str,
    ) -> Path:

        return self._directory(

            "silver",

            provider,

            product,

        )
        # ======================================================
    # GOLD PATH
    # ======================================================

    def gold_path(
        self,
        provider: str,
        product: str,
    ) -> Path:

        return self._directory(

            "gold",

            provider,

            product,

        )
        # ======================================================
    # METADATA PATH
    # ======================================================

    def metadata_path(
        self,
        provider: str,
        product: str,
    ) -> Path:

        return self._directory(

            "metadata",

            provider,

            product,

        )
        # ======================================================
    # LOGS PATH
    # ======================================================

    def logs_path(
        self,
        provider: str,
        product: str,
    ) -> Path:

        return self._directory(

            "logs",

            provider,

            product,

        )
        # ======================================================
    # TEMP PATH
    # ======================================================

    def temp_path(
        self,
        provider: str,
        product: str,
    ) -> Path:

        return self._directory(

            "temp",

            provider,

            product,

        )
        # ======================================================
    # SAVE BYTES
    # ======================================================

    def save_bytes(
        self,
        path: Path,
        data: bytes,
        overwrite: bool = False,
    ) -> Path:
        """
        Save bytes to a file.
        """

        path = Path(path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if path.exists() and not overwrite:

            raise FileExistsError(
                f"File already exists: {path}"
            )

        path.write_bytes(data)

        logger.info(
            f"Saved {len(data):,} bytes -> {path}"
        )

        return path
        # ======================================================
    # READ BYTES
    # ======================================================

    def read_bytes(
        self,
        path: Path,
    ) -> bytes:
        """
        Read an entire file as bytes.
        """

        path = Path(path)

        if not path.exists():

            raise FileNotFoundError(path)

        return path.read_bytes()
        # ======================================================
    # FILE EXISTS
    # ======================================================

    def exists(
        self,
        path: Path,
    ) -> bool:

        return Path(path).exists()
        # ======================================================
    # DELETE FILE
    # ======================================================

    def delete(
        self,
        path: Path,
        missing_ok: bool = True,
    ) -> None:
        """
        Delete a file.
        """

        path = Path(path)

        if not path.exists():

            if missing_ok:

                return

            raise FileNotFoundError(path)

        path.unlink()

        logger.info(
            f"Deleted {path}"
        )
            # ======================================================
    # ENSURE DIRECTORY
    # ======================================================

    def ensure_directory(
        self,
        path: Path,
    ) -> Path:
        """
        Create a directory if it does not exist.
        """

        path = Path(path)

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path
        # ======================================================
    # LIST FILES
    # ======================================================

    def list_files(
        self,
        directory: Path,
        pattern: str = "*",
    ) -> list[Path]:
        """
        Return all files matching a pattern.
        """

        directory = Path(directory)

        if not directory.exists():

            return []

        return sorted(

            file

            for file in directory.glob(pattern)

            if file.is_file()

        )
        # ======================================================
    # MOVE FILE
    # ======================================================

    def move(
        self,
        source: Path,
        destination: Path,
        overwrite: bool = False,
    ) -> Path:
        """
        Move a file.
        """

        source = Path(source)
        destination = Path(destination)

        if not source.exists():

            raise FileNotFoundError(source)

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if destination.exists():

            if not overwrite:

                raise FileExistsError(destination)

            destination.unlink()

        shutil.move(
            str(source),
            str(destination),
        )

        logger.info(

            f"Moved {source} -> {destination}"

        )

        return destination
        # ======================================================
    # COPY FILE
    # ======================================================

    def copy(
        self,
        source: Path,
        destination: Path,
        overwrite: bool = False,
    ) -> Path:
        """
        Copy a file.
        """

        source = Path(source)
        destination = Path(destination)

        if not source.exists():

            raise FileNotFoundError(source)

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if destination.exists():

            if not overwrite:

                raise FileExistsError(destination)

            destination.unlink()

        shutil.copy2(
            source,
            destination,
        )

        logger.info(

            f"Copied {source} -> {destination}"

        )

        return destination
        # ======================================================
    # TEMPORARY FILE
    # ======================================================

    def temporary_file(
        self,
        suffix: str = "",
    ) -> Path:
        """
        Return a unique temporary file path.
        """

        temp_dir = self.root / "temp"

        temp_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (

            f"{uuid.uuid4().hex}{suffix}"

        )

        return temp_dir / filename