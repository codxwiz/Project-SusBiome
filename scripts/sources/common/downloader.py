"""
============================================================
SusBiome Downloader
============================================================

Purpose
-------
Central HTTP download engine.

Responsibilities

✓ Download files

✓ Stream large downloads

✓ Write to temporary storage

✓ Return download metadata

No parsing.
No manifests.
No provider logic.

============================================================
"""
from __future__ import annotations

from requests.exceptions import (
    RequestException,
    Timeout,
    ConnectionError,
)
import shutil
import logging
import time

from dataclasses import dataclass
from pathlib import Path

import requests

from requests import Session

from scripts.sources.common.auth import AuthManager
from scripts.sources.common.storage import Storage
from scripts.sources.common.config import (

    HTTP_TIMEOUT,

    DOWNLOAD_CHUNK_SIZE,

)

MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 30.0

logger = logging.getLogger(

    "susbiome.downloader"

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
# DOWNLOAD RESULT
# ==========================================================

@dataclass(slots=True)
class DownloadResult:

    url: str

    final_url: str

    destination: Path

    status_code: int

    downloaded_bytes: int

    content_length: int | None

    content_type: str | None

    elapsed_seconds: float

    success: bool
    # ==========================================================
# DOWNLOADER
# ==========================================================

class Downloader:

    """
    Central HTTP downloader.
    """
    def __init__(

        self,

        auth: AuthManager,

        storage: Storage,

    ):

        self.auth = auth

        self.storage = storage
            # ======================================================
    # RETRYABLE ERROR
    # ======================================================

    @staticmethod
    def _is_retryable(
        error: Exception,
    ) -> bool:

        return isinstance(

            error,

            (

                Timeout,

                ConnectionError,

                RequestException,

            ),

        )
        # ======================================================
    # SINGLE DOWNLOAD ATTEMPT
    # ======================================================

    def _download_once(
        self,
        *,
        session: Session,
        url: str,
        destination: Path,
    ) -> DownloadResult:

        temp_file = self.storage.temporary_file(
            suffix=".download"
        )
        try:

            start = time.perf_counter()

            downloaded = 0

            response = session.get(
                url,
                stream=True,
                timeout=HTTP_TIMEOUT,
            )

            response.raise_for_status()

            content_length = response.headers.get(
                "Content-Length"
            )

            if content_length is not None:
                content_length = int(content_length)

            content_type = response.headers.get(
                "Content-Type"
            )

            final_url = response.url

            log_interval = 50 * 1024 * 1024
            next_log = log_interval

            with temp_file.open("wb") as fp:
                for chunk in response.iter_content(
                    chunk_size=DOWNLOAD_CHUNK_SIZE
                ):
                    if not chunk:
                        continue

                    fp.write(chunk)
                    downloaded += len(chunk)

                    if downloaded >= next_log:
                        logger.info(
                            f"Downloaded "
                            f"{downloaded / (1024 * 1024):.1f} MB"
                        )
                        next_log += log_interval

            if (
                content_length is not None
                and
                downloaded != content_length
            ):
                raise IOError(
                    "Downloaded file size "
                    "does not match "
                    "Content-Length."
                )

            self.storage.ensure_directory(
                destination.parent
            )

            self.storage.move(
                temp_file,
                destination,
                overwrite=False,
            )

            elapsed = time.perf_counter() - start

            return DownloadResult(
                url=url,
                final_url=final_url,
                destination=destination,
                status_code=response.status_code,
                downloaded_bytes=downloaded,
                content_length=content_length,
                content_type=content_type,
                elapsed_seconds=elapsed,
                success=True,
            )
        except Exception:

            if self.storage.exists(
                temp_file
            ):

                self.storage.delete(
                    temp_file
                )

            raise
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
               # ======================================================
    # DOWNLOAD
    # ======================================================

    def download(
        self,
        *,
        provider: str,
        url: str,
        destination: Path,
    ) -> DownloadResult:
        """
        Download a file with automatic retry handling.
        """

        session = self.auth.session(
            provider
        )

        last_exception: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):

            try:

                return self._download_once(

                    session=session,

                    url=url,

                    destination=destination,

                )

            except Exception as exc:

                last_exception = exc

                if not self._is_retryable(exc):

                    logger.exception(

                        "Non-retryable download error."

                    )

                    raise

                if attempt == MAX_RETRIES:

                    logger.exception(

                        "Maximum retries exceeded."

                    )

                    raise

                wait = min(

                    INITIAL_RETRY_DELAY
                    * (2 ** (attempt - 1)),

                    MAX_RETRY_DELAY,

                )

                logger.warning(

                    f"Download attempt "

                    f"{attempt}/{MAX_RETRIES} "

                    f"failed. "

                    f"Retrying in {wait} seconds."

                )

                time.sleep(wait)

        raise RuntimeError(

            "Downloader exited unexpectedly."

        ) from last_exception
        # ======================================================
    # HEAD
    # ======================================================

    def head(
        self,
        *,
        provider: str,
        url: str,
    ) -> requests.Response:
        """
        Execute an authenticated HTTP HEAD request.
        """

        session = self.auth.session(
            provider
        )

        response = session.head(

            url,

            timeout=HTTP_TIMEOUT,

            allow_redirects=True,

        )

        response.raise_for_status()

        return response
        # ======================================================
    # CLOSE
    # ======================================================

    def close(
        self,
    ) -> None:
        """
        Release downloader resources.
        """

        self.auth.close()

        logger.info(

            "Downloader closed."

        )
    