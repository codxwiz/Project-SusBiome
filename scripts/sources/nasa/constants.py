"""
============================================================
NASA Constants
============================================================

Purpose
-------
Central NASA constants for the SusBiome platform.

This module contains immutable NASA metadata used by all
NASA source modules.

No networking.
No authentication.
No filesystem logic.

============================================================
"""

from __future__ import annotations

# ==========================================================
# PROVIDER
# ==========================================================

NASA_PROVIDER = "NASA"

EARTHDATA_PROVIDER = "Earthdata"

# ==========================================================
# SERVICES
# ==========================================================

EARTHDATA_HOST = "https://earthdata.nasa.gov"

CMR_HOST = "https://cmr.earthdata.nasa.gov"

# ==========================================================
# CMR ENDPOINTS
# ==========================================================

CMR_SEARCH_API = (
    f"{CMR_HOST}/search"
)

CMR_GRANULES_URL = (
    f"{CMR_SEARCH_API}/granules.json"
)

CMR_COLLECTIONS_URL = (
    f"{CMR_SEARCH_API}/collections.json"
)

# ==========================================================
# GPM PRODUCTS
# ==========================================================

GPM_PRODUCT = "GPM"

IMERG_EARLY = "IMERG Early Run"

IMERG_LATE = "IMERG Late Run"

IMERG_FINAL = "IMERG Final Run"

SUPPORTED_GPM_PRODUCTS = (

    IMERG_EARLY,

    IMERG_LATE,

    IMERG_FINAL,

)

# ==========================================================
# PRODUCT VERSION
# ==========================================================

CURRENT_IMERG_VERSION = "V07"

# ==========================================================
# FILE EXTENSIONS
# ==========================================================

NETCDF_EXTENSION = ".nc4"

HDF5_EXTENSION = ".h5"

XML_EXTENSION = ".xml"

JSON_EXTENSION = ".json"

# ==========================================================
# MIME TYPES
# ==========================================================

CONTENT_TYPE_JSON = "application/json"

CONTENT_TYPE_NETCDF = "application/x-netcdf"

CONTENT_TYPE_HDF5 = "application/x-hdf5"

CONTENT_TYPE_XML = "application/xml"

# ==========================================================
# HTTP HEADERS
# ==========================================================

HEADER_CONTENT_TYPE = "Content-Type"

HEADER_CONTENT_LENGTH = "Content-Length"

HEADER_LAST_MODIFIED = "Last-Modified"

HEADER_ETAG = "ETag"

# ==========================================================
# CMR PARAMETERS
# ==========================================================

PARAM_PAGE_SIZE = "page_size"

PARAM_PAGE_NUM = "page_num"

PARAM_CONCEPT_ID = "concept_id"

PARAM_TEMPORAL = "temporal"

PARAM_SHORT_NAME = "short_name"

PARAM_VERSION = "version"

PARAM_PROVIDER = "provider"

PARAM_SORT_KEY = "sort_key"

# ==========================================================
# DEFAULT QUERY VALUES
# ==========================================================

DEFAULT_PAGE_SIZE = 2000

DEFAULT_SORT_KEY = "-start_date"

# ==========================================================
# RESPONSE KEYS
# ==========================================================

KEY_FEED = "feed"

KEY_ENTRY = "entry"

KEY_LINKS = "links"

KEY_TITLE = "title"

KEY_ID = "id"

KEY_UPDATED = "updated"

KEY_TIME_START = "time_start"

KEY_TIME_END = "time_end"

KEY_HREF = "href"

KEY_TYPE = "type"