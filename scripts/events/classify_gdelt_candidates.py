"""
============================================================
SusBiome
Classify GDELT Candidates
Version : 2.0
============================================================

Purpose
-------
Convert candidate GDELT events into validated
Ground Truth records.

Input
-----
data/silver/events/gdelt_candidate_events.parquet

Output
------
data/bronze/ground_truth/gdelt_ground_truth.parquet

============================================================
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys

from datetime import UTC, datetime, timezone
from pathlib import Path

import pandas as pd

from ground_truth.schemas.ground_truth_schema import (

    GroundTruthRecord,

    SourceType,

    HazardType,

    HazardSubtype,

    Severity,

    AdminLevel,

    LocationSource,

    GROUND_TRUTH_COLUMNS

)

# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT /
    "data/silver/events/gdelt_candidate_events.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT /
    "data/bronze/ground_truth"
)

OUTPUT_FILE = (
    OUTPUT_DIR /
    "gdelt_ground_truth.parquet"
)

OUTPUT_CSV = (
    OUTPUT_DIR /
    "gdelt_ground_truth.csv"
)

LOG_DIR = (
    PROJECT_ROOT /
    "data/bronze/ground_truth/logs"
)

SUMMARY_FILE = (
    LOG_DIR /
    "classify_gdelt_summary.json"
)

LOG_FILE = (
    LOG_DIR /
    "classify_gdelt.log"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True)

# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(

    level=logging.INFO,

    format="%(asctime)s | %(levelname)s | %(message)s",

    handlers=[

        logging.FileHandler(LOG_FILE),

        logging.StreamHandler(sys.stdout)

    ]

)

logger = logging.getLogger(__name__)

# ==========================================================
# CLI
# ==========================================================

def parse_args():

    parser = argparse.ArgumentParser(

        description="Classify GDELT candidate events"

    )

    parser.add_argument(

        "--csv",

        action="store_true",

        help="Also export CSV"

    )

    return parser.parse_args()

# ==========================================================
# LOAD DATASET
# ==========================================================

def load_candidates():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(

            f"Candidate file not found:\n{INPUT_FILE}"

        )

    df = pd.read_parquet(

        INPUT_FILE

    )

    logger.info(

        f"Loaded {len(df):,} candidate events."

    )

    return df

# ==========================================================
# VALIDATE INPUT
# ==========================================================

REQUIRED_COLUMNS = [

    "candidate_id",

    "gdelt_event_id",

    "event_date",

    "state",

    "district",

    "candidate_score",

    "candidate_reason",

    "needs_review",

    "headline",

    "description",

    "source_url"

]

def validate_input(df):

    missing = [

        c

        for c in REQUIRED_COLUMNS

        if c not in df.columns

    ]

    if missing:

        raise ValueError(

            f"Missing columns: {missing}"

        )

    logger.info(

        "Candidate schema validated."

    )

# ==========================================================
# TEXT
# ==========================================================

def normalize(text):

    if pd.isna(text):

        return ""

    return str(text).lower().strip()

def combined_text(row):

    return " ".join([

        normalize(

            row.get("headline","")

        ),

        normalize(

            row.get("description","")

        ),

        normalize(

            row.get("candidate_reason","")

        ),

        normalize(

            row.get("source_url","")

        )

    ])
# ==========================================================
# HAZARD MAPPING
# ==========================================================

HAZARD_KEYWORDS = {

    HazardType.FLOOD: {

        "keywords": [

            "flood",
            "flash flood",
            "river flood",
            "river overflow",
            "embankment",
            "inundation",
            "waterlogging"

        ],

        "subtypes": {

            "flash flood":
                HazardSubtype.FLASH_FLOOD,

            "river flood":
                HazardSubtype.RIVER_FLOOD

        }

    },

    HazardType.DROUGHT: {

        "keywords": [

            "drought",
            "dry spell",
            "rainfall deficit",
            "water shortage"

        ],

        "subtypes": {}

    },

    HazardType.CYCLONE: {

        "keywords": [

            "cyclone",
            "cyclonic storm",
            "storm surge",
            "landfall"

        ],

        "subtypes": {

            "cyclonic storm":
                HazardSubtype.CYCLONIC_STORM,

            "cyclone":
                HazardSubtype.TROPICAL_CYCLONE

        }

    },

    HazardType.LANDSLIDE: {

        "keywords": [

            "landslide",
            "mudslide"

        ],

        "subtypes": {

            "landslide":
                HazardSubtype.LANDSLIDE

        }

    },

    HazardType.HEATWAVE: {

        "keywords": [

            "heatwave",
            "heat wave"

        ],

        "subtypes": {

            "heatwave":
                HazardSubtype.HEATWAVE

        }

    },

    HazardType.COLD_WAVE: {

        "keywords": [

            "cold wave",
            "coldwave"

        ],

        "subtypes": {

            "cold wave":
                HazardSubtype.COLD_WAVE

        }

    }

}

# ==========================================================
# CLASSIFICATION
# ==========================================================

def classify_event(text):

    for hazard, config in HAZARD_KEYWORDS.items():

        for keyword in config["keywords"]:

            if keyword in text:

                subtype = config["subtypes"].get(
                    keyword
                )

                return (

                    hazard,

                    subtype,

                    keyword

                )

    return (None, None, "")


def parse_event_date(value):
    """Parse GDELT SQLDATE values without treating integers as nanoseconds."""
    if pd.isna(value):
        raise ValueError("Missing event date.")
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if re.fullmatch(r"\d{8}", text):
        return pd.to_datetime(text, format="%Y%m%d", errors="raise").date()
    return pd.to_datetime(text, errors="raise").date()

# ==========================================================
# SEVERITY
# ==========================================================

def estimate_severity(score):

    if score >= 80:

        return Severity.EXTREME

    if score >= 60:

        return Severity.SEVERE

    if score >= 40:

        return Severity.MODERATE

    return Severity.MINOR

# ==========================================================
# CONFIDENCE
# ==========================================================

def estimate_confidence(row):

    score = float(

        row.get(

            "candidate_score",

            0

        )

    )

    if row.get(

        "needs_review",

        False

    ):

        score *= 0.85

    return round(

        min(

            score,

            100

        ),

        2

    )

# ==========================================================
# BUILD ONE RECORD
# ==========================================================

def build_record(row):

    text = combined_text(row)

    hazard, subtype, keyword = classify_event(

        text

    )

    if hazard is None:
        return None

    confidence = estimate_confidence(

        row

    )

    record = GroundTruthRecord(

        source=SourceType.GDELT,

        source_event_id=str(

            row["gdelt_event_id"]

        ),

        event_date=parse_event_date(row["event_date"]),

        hazard_type=hazard,

        hazard_subtype=subtype,

        severity=estimate_severity(

            confidence

        ),

        country="India",

        state=row["state"],

        district=(
            None
            if row["district"] == "UNKNOWN"
            else row["district"]
        ),

        admin_level=AdminLevel.STATE,

        location_source=LocationSource.STATE,

        headline=row.get(

            "headline"

        ),

        description=row.get(

            "description"

        ),

        source_name="GDELT",

        source_url=row.get(

            "source_url"

        ),

        confidence=confidence,

        verified=not bool(

            row["needs_review"]

        )

    )

    return record.model_dump()

# ==========================================================
# BUILD DATAFRAME
# ==========================================================

# ==========================================================
# BUILD GROUND TRUTH DATASET
# ==========================================================

def build_ground_truth(df):

    records = []

    skipped = 0

    for _, row in df.iterrows():

        try:

            record = build_record(row)

            if record is None:

                skipped += 1

                continue

            records.append(record)

        except Exception as exc:

            skipped += 1

            logger.warning(

                f"Skipped candidate "
                f"{row.get('candidate_id')} : "
                f"{exc}"

            )

    if not records:

        logger.warning(

            "No Ground Truth records were generated."

        )

        return pd.DataFrame(

            columns=GROUND_TRUTH_COLUMNS

        )

    out = pd.DataFrame.from_records(records)

    out = out.reindex(

        columns=GROUND_TRUTH_COLUMNS

    )

    logger.info(

        f"Ground Truth records : {len(out):,}"

    )

    logger.info(

        f"Skipped records      : {skipped:,}"

    )

    return out
# ==========================================================
# WRITE OUTPUT
# ==========================================================

def write_output(df, export_csv=False):

    if df.empty:

        logger.warning(
            "Ground Truth dataset is empty."
        )

        return

    df.to_parquet(
        OUTPUT_FILE,
        index=False
    )

    logger.info(
        f"Parquet written: {OUTPUT_FILE}"
    )

    if export_csv:

        df.to_csv(
            OUTPUT_CSV,
            index=False
        )

        logger.info(
            f"CSV written: {OUTPUT_CSV}"
        )


# ==========================================================
# SUMMARY
# ==========================================================

def build_summary(df):

    if df.empty:

        return {

            "created_at":
                datetime.now(UTC).isoformat(),

            "records": 0,

            "verified": 0,

            "needs_review": 0,

            "hazards": {},

            "states": {}

        }

    return {

        "created_at":
            datetime.now(UTC).isoformat(),

        "records":
            int(len(df)),

        "verified":
            int(df["verified"].sum()),

        "needs_review":
            int((~df["verified"]).sum()),

        "hazards":
            df["hazard_type"]
              .value_counts()
              .to_dict(),

        "states":
            df["state"]
              .value_counts()
              .to_dict(),

        "average_confidence":
            round(
                float(
                    df["confidence"].mean()
                ),
                2
            )

    }


# ==========================================================
# JSON SAFE
# ==========================================================

def json_safe(value):

    import numpy as np

    if isinstance(value, dict):

        return {

            k: json_safe(v)

            for k, v in value.items()

        }

    if isinstance(value, list):

        return [

            json_safe(v)

            for v in value

        ]

    if isinstance(
        value,
        (
            np.integer,
            np.int64,
            np.int32
        )
    ):

        return int(value)

    if isinstance(
        value,
        (
            np.floating,
            np.float64,
            np.float32
        )
    ):

        return float(value)

    return value


# ==========================================================
# WRITE SUMMARY
# ==========================================================

def write_summary(summary):

    with open(

        SUMMARY_FILE,

        "w",

        encoding="utf-8"

    ) as f:

        json.dump(

            json_safe(summary),

            f,

            indent=4

        )

    logger.info(

        f"Summary written: {SUMMARY_FILE}"

    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    args = parse_args()

    start = datetime.now(UTC)

    print()

    print("=" * 60)

    print("CLASSIFY GDELT CANDIDATES")

    print("=" * 60)

    try:

        candidates = load_candidates()

        validate_input(

            candidates

        )

        ground_truth = build_ground_truth(

            candidates

        )

        write_output(

            ground_truth,

            args.csv

        )

        summary = build_summary(

            ground_truth

        )

        write_summary(

            summary

        )

        elapsed = (

            datetime.now(UTC) -

            -

            start

        ).total_seconds()

        print()

        print("=" * 60)

        print("CLASSIFICATION COMPLETE")

        print("=" * 60)

        print(

            f"Ground Truth : {len(ground_truth):,}"

        )

        print(

            f"Parquet      : {OUTPUT_FILE}"

        )

        if args.csv:

            print(

                f"CSV          : {OUTPUT_CSV}"

            )

        print(

            f"Summary      : {SUMMARY_FILE}"

        )

        print(

            f"Elapsed      : {elapsed:.2f}s"

        )

        print()

    except Exception as exc:

        logger.exception(exc)

        print()

        print("=" * 60)

        print("CLASSIFICATION FAILED")

        print("=" * 60)

        print(exc)

        print()

        raise


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    main()
