"""
============================================================
NASA Earthdata Discovery
============================================================

Purpose
-------
Discover NASA datasets using the Earthdata CMR Search API.

Responsibilities

✓ Build CMR queries

✓ Retrieve CMR responses

✓ Validate responses

✓ Parse granules

✓ Return strongly typed Granule objects

No downloading.
No storage.
No manifest registration.

============================================================
"""

from __future__ import annotations

import logging

from datetime import datetime
from typing import Any

from scripts.sources.nasa.client import NASAClient

from scripts.sources.nasa.models import (

    Product,

    Granule,

)

from scripts.sources.nasa.exceptions import (

    NASADiscoveryError,

    NASAResponseError,

)

from scripts.sources.nasa.constants import (

    CMR_GRANULES_URL,

    PARAM_SHORT_NAME,

    PARAM_VERSION,

    PARAM_TEMPORAL,

    PARAM_PAGE_SIZE,

    DEFAULT_PAGE_SIZE,

    KEY_FEED,

    KEY_ENTRY,

    KEY_LINKS,

    KEY_ID,

    KEY_TIME_START,

    KEY_TIME_END,

    KEY_HREF,

)

logger = logging.getLogger(__name__)

# ==========================================================
# NASA DISCOVERY
# ==========================================================

class NASAEarthdataDiscovery:
    """
    Discover NASA datasets through CMR.
    """
    def __init__(
        self,
        client: NASAClient | None = None,
    ) -> None:

        self.client = client or NASAClient()
            # ======================================================
    # BUILD QUERY
    # ======================================================

    def _build_query(
        self,
        product: Product,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        """
        Build a CMR granule search query.
        """

        return {

            PARAM_SHORT_NAME:

                product.product,

            PARAM_VERSION:

                product.version,

            PARAM_TEMPORAL:

                (
                    f"{start.isoformat()}Z,"
                    f"{end.isoformat()}Z"
                ),

            PARAM_PAGE_SIZE:

                DEFAULT_PAGE_SIZE,

        }
        # ======================================================
    # REQUEST
    # ======================================================

    def _request(
        self,
        query: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a CMR granule search.
        """

        logger.info(

            "Querying NASA CMR."

        )

        try:

            response = self.client.get_json(

                CMR_GRANULES_URL,

                params=query,

            )

        except Exception as exc:

            raise NASADiscoveryError(

                "Failed to query NASA CMR."

            ) from exc

        return response
        # ======================================================
    # VALIDATE RESPONSE
    # ======================================================

    def _validate_response(
        self,
        response: dict[str, Any],
    ) -> None:
        """
        Validate the structure of a CMR response.
        """

        if not isinstance(response, dict):

            raise NASAResponseError(

                "CMR response is not a JSON object."

            )

        if KEY_FEED not in response:

            raise NASAResponseError(

                "Missing 'feed' object."

            )

        feed = response[KEY_FEED]

        if not isinstance(feed, dict):

            raise NASAResponseError(

                "'feed' must be an object."

            )

        if KEY_ENTRY not in feed:

            raise NASAResponseError(

                "Missing 'entry' list."

            )

        if not isinstance(feed[KEY_ENTRY], list):

            raise NASAResponseError(

                "'entry' must be a list."

            )
            # ======================================================
    # GET ENTRIES
    # ======================================================

    def _get_entries(
        self,
        response: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Return the CMR entry list.
        """

        self._validate_response(

            response

        )

        return response[KEY_FEED][KEY_ENTRY]
            # ======================================================
    # PARSE LINKS
    # ======================================================

    def _parse_links(
        self,
        entry: dict[str, Any],
    ) -> str:
        """
        Return the primary downloadable URL for a granule.
        """

        links = entry.get(KEY_LINKS, [])

        if not isinstance(links, list):

            raise NASAResponseError(
                "Invalid CMR links."
            )

        #
        # Prefer downloadable data links.
        #
        for link in links:

            href = link.get(KEY_HREF)

            if not isinstance(href, str):

                continue

            if href.endswith(".nc4"):

                return href

            if href.endswith(".h5"):

                return href

        #
        # Fallback to first valid URL.
        #
        for link in links:

            href = link.get(KEY_HREF)

            if isinstance(href, str):

                return href

        raise NASAResponseError(

            "No downloadable URL found."

        )
        # ======================================================
    # PARSE GRANULE
    # ======================================================

    def _parse_granule(
        self,
        product: Product,
        entry: dict[str, Any],
    ) -> Granule:
        """
        Convert one CMR entry into a Granule.
        """

        granule_id = entry.get(

            KEY_ID

        )

        if not granule_id:

            raise NASAResponseError(

                "Missing granule id."

            )

        start_time = datetime.fromisoformat(

            entry[KEY_TIME_START].replace(

                "Z",

                "+00:00",

            )

        )

        end_time = datetime.fromisoformat(

            entry[KEY_TIME_END].replace(

                "Z",

                "+00:00",

            )

        )

        return Granule(

            granule_id=granule_id,

            product=product,

            start_time=start_time,

            end_time=end_time,

            url=self._parse_links(

                entry

            ),

        )
        # ======================================================
    # PARSE FEED
    # ======================================================

    def _parse_feed(
        self,
        product: Product,
        response: dict[str, Any],
    ) -> list[Granule]:
        """
        Parse every CMR entry.
        """

        granules: list[Granule] = []

        entries = self._get_entries(

            response

        )

        for entry in entries:

            granules.append(

                self._parse_granule(

                    product,

                    entry,

                )

            )

        return granules
        # ======================================================
    # DISCOVER
    # ======================================================

    def discover(
        self,
        product: Product,
        start: datetime,
        end: datetime,
    ) -> list[Granule]:
        """
        Discover NASA granules.
        """

        logger.info(

            f"Discovering "

            f"{product.product} "

            f"{product.version}"

        )

        query = self._build_query(

            product,

            start,

            end,

        )

        response = self._request(

            query

        )

        granules = self._parse_feed(

            product,

            response,

        )

        logger.info(

            f"Discovered "

            f"{len(granules)} "

            f"granules."

        )

        return granules
        # ======================================================
    # CLOSE
    # ======================================================

    def close(
        self,
    ) -> None:
        """
        Release resources.
        """

        self.client.close()