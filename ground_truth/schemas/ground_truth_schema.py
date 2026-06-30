"""
============================================================
SusBiome Ground Truth Schema v1.0
============================================================

Canonical schema for every historical disaster record.

Every collector MUST produce this schema.

Collectors:
    - News
    - GDELT
    - EM-DAT
    - NDMA
    - IMD
    - Future Sources

Author:
    SusBiome
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict, field_validator

# ==========================================================
# SCHEMA VERSION
# ==========================================================

GROUND_TRUTH_SCHEMA_VERSION = "1.0"


# ==========================================================
# ENUMS
# ==========================================================

class SourceType(str, Enum):
    NEWS = "NEWS"
    GDELT = "GDELT"
    EMDAT = "EMDAT"
    NDMA = "NDMA"
    IMD = "IMD"
    IBTRACS = "IBTRACS"
    GDACS = "GDACS"


class HazardType(str, Enum):
    FLOOD = "FLOOD"
    DROUGHT = "DROUGHT"
    CYCLONE = "CYCLONE"
    LANDSLIDE = "LANDSLIDE"
    HEATWAVE = "HEATWAVE"
    COLD_WAVE = "COLD_WAVE"


class HazardSubtype(str, Enum):

    RIVER_FLOOD = "RIVER_FLOOD"
    FLASH_FLOOD = "FLASH_FLOOD"
    URBAN_FLOOD = "URBAN_FLOOD"
    COASTAL_FLOOD = "COASTAL_FLOOD"

    METEOROLOGICAL_DROUGHT = "METEOROLOGICAL_DROUGHT"
    AGRICULTURAL_DROUGHT = "AGRICULTURAL_DROUGHT"
    HYDROLOGICAL_DROUGHT = "HYDROLOGICAL_DROUGHT"

    TROPICAL_CYCLONE = "TROPICAL_CYCLONE"
    CYCLONIC_STORM = "CYCLONIC_STORM"
    SEVERE_CYCLONIC_STORM = "SEVERE_CYCLONIC_STORM"
    VERY_SEVERE_CYCLONIC_STORM = "VERY_SEVERE_CYCLONIC_STORM"
    EXTREMELY_SEVERE_CYCLONIC_STORM = "EXTREMELY_SEVERE_CYCLONIC_STORM"

    LANDSLIDE = "LANDSLIDE"
    HEATWAVE = "HEATWAVE"
    COLD_WAVE = "COLD_WAVE"


class Severity(str, Enum):
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    EXTREME = "EXTREME"


class AdminLevel(str, Enum):
    COUNTRY = "COUNTRY"
    STATE = "STATE"
    DISTRICT = "DISTRICT"
    SUBDISTRICT = "SUBDISTRICT"
    VILLAGE = "VILLAGE"
    POINT = "POINT"


class LocationSource(str, Enum):
    COUNTRY = "COUNTRY"
    STATE = "STATE"
    DISTRICT = "DISTRICT"
    GEOCODED = "GEOCODED"
    GPS = "GPS"
    MANUAL = "MANUAL"


# ==========================================================
# MODEL
# ==========================================================

class GroundTruthRecord(BaseModel):

    # ------------------------------------------------------
    # Identity
    # ------------------------------------------------------

    schema_version: str = Field(
        default=GROUND_TRUTH_SCHEMA_VERSION,
        frozen=True,
        description="Ground Truth Schema Version"
    )

    event_id: str = Field(
        default_factory=lambda: f"EVT_{uuid4().hex}"
    )

    source: SourceType

    source_event_id: Optional[str] = None

    # ------------------------------------------------------
    # Event
    # ------------------------------------------------------

    event_date: date

    hazard_type: HazardType

    hazard_subtype: Optional[HazardSubtype] = None

    severity: Optional[Severity] = None

    # ------------------------------------------------------
    # Geography
    # ------------------------------------------------------

    country: str = "India"

    state: str

    district: Optional[str] = None

    subdistrict: Optional[str] = None

    village: Optional[str] = None

    admin_level: AdminLevel = AdminLevel.STATE

    latitude: Optional[float] = None

    longitude: Optional[float] = None

    location_source: LocationSource = LocationSource.STATE

    # ------------------------------------------------------
    # Impact
    # ------------------------------------------------------

    fatalities: Optional[int] = None

    injured: Optional[int] = None

    displaced: Optional[int] = None

    affected_population: Optional[int] = None

    economic_loss: Optional[float] = None

    # ------------------------------------------------------
    # Metadata
    # ------------------------------------------------------

    headline: Optional[str] = None

    description: Optional[str] = None

    source_name: Optional[str] = None

    source_url: Optional[str] = None

    # ------------------------------------------------------
    # Quality
    # ------------------------------------------------------

    confidence: Optional[float] = Field(
        default=None,
        ge=0,
        le=100
    )

    verified: bool = False

    # ------------------------------------------------------
    # Audit
    # ------------------------------------------------------

    collected_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    # ------------------------------------------------------
    # Validators
    # ------------------------------------------------------

    @field_validator("country")
    @classmethod
    def validate_country(cls, value):

        if not value:
            raise ValueError("Country cannot be empty.")

        return value

    @field_validator("state")
    @classmethod
    def validate_state(cls, value):

        if not value:
            raise ValueError("State cannot be empty.")

        return value

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value):

        if value is None:
            return value

        if value < -90 or value > 90:
            raise ValueError("Invalid latitude.")

        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value):

        if value is None:
            return value

        if value < -180 or value > 180:
            raise ValueError("Invalid longitude.")

        return value

    @field_validator(
        "fatalities",
        "injured",
        "displaced",
        "affected_population"
    )
    @classmethod
    def validate_positive(cls, value):

        if value is None:
            return value

        if value < 0:
            raise ValueError("Negative values are not allowed.")

        return value


# ==========================================================
# HELPERS
# ==========================================================

def empty_record(source: SourceType) -> GroundTruthRecord:
    """
    Create an empty record for a collector.
    """

    return GroundTruthRecord(
        source=source,
        event_date=date.today(),
        state="UNKNOWN",
        hazard_type=HazardType.FLOOD
    )


# ==========================================================
# CANONICAL COLUMN ORDER
# ==========================================================

GROUND_TRUTH_COLUMNS = [
    "schema_version",
    "event_id",
    "source",
    "source_event_id",

    "event_date",

    "hazard_type",
    "hazard_subtype",
    "severity",

    "country",
    "state",
    "district",
    "subdistrict",
    "village",

    "admin_level",

    "latitude",
    "longitude",

    "location_source",

    "fatalities",
    "injured",
    "displaced",
    "affected_population",
    "economic_loss",

    "headline",
    "description",

    "source_name",
    "source_url",

    "confidence",
    "verified",

    "collected_at"

]
