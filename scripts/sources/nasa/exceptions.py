"""
============================================================
NASA Exceptions
============================================================

Purpose
-------
Custom exception hierarchy for NASA source modules.

These exceptions are raised only by NASA-specific modules.

============================================================
"""

from __future__ import annotations


# ==========================================================
# BASE
# ==========================================================

class NASAError(Exception):
    """
    Base class for all NASA-related exceptions.
    """


# ==========================================================
# AUTHENTICATION
# ==========================================================

class NASAAuthenticationError(NASAError):
    """
    Authentication with NASA Earthdata failed.
    """


# ==========================================================
# REQUEST
# ==========================================================

class NASARequestError(NASAError):
    """
    NASA API request failed.
    """


# ==========================================================
# DISCOVERY
# ==========================================================

class NASADiscoveryError(NASAError):
    """
    Failed to discover NASA datasets.
    """


# ==========================================================
# PARSING
# ==========================================================

class NASAResponseError(NASAError):
    """
    Invalid or unexpected NASA response.
    """


# ==========================================================
# DOWNLOAD
# ==========================================================

class NASADownloadError(NASAError):
    """
    NASA download failed.
    """


# ==========================================================
# PRODUCT
# ==========================================================

class NASAProductError(NASAError):
    """
    Invalid or unsupported NASA product.
    """