"""
============================================================
SusBiome
Ground Truth Collector - News
Version : 1.0
============================================================

Purpose
-------
Converts verified news events into canonical
GroundTruthRecord objects.

Input
-----
CSV or Parquet

Output
------
news_ground_truth.parquet

Author
------
SusBiome
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ground_truth.schemas.ground_truth_schema import (
    GroundTruthRecord,
    SourceType,
    HazardType,
)

# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_CSV = (
    PROJECT_ROOT
    / "data/silver/events/verified_events_final.csv"
)

INPUT_PARQUET = (
    PROJECT_ROOT
    / "data/silver/events/verified_events_final.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data/bronze/ground_truth"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "news_ground_truth.parquet"
)

LOG_DIR = (
    OUTPUT_DIR
    / "logs"
)

LOG_FILE = (
    LOG_DIR
    / "collect_news_groundtruth.log"
)

SUMMARY_FILE = (
    LOG_DIR
    / "collect_news_groundtruth_summary.json"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

# ==========================================================
# REQUIRED INPUT COLUMNS
# ==========================================================

REQUIRED_COLUMNS = {

    "date",

    "state_query",

    "event_type",

    "headline",

    "description",

    "source",

    "url",

}

OPTIONAL_COLUMNS = {

    "district",

    "content",

    "author",

    "verification_score",

    "latitude",

    "longitude",

    "fatalities",

    "injured",

    "displaced",

    "affected_population",

    "economic_loss",

}

# ==========================================================
# HAZARD NORMALIZATION
# ==========================================================

HAZARD_MAP = {

    "flood": HazardType.FLOOD,

    "flooding": HazardType.FLOOD,

    "river flood": HazardType.FLOOD,

    "flash flood": HazardType.FLOOD,

    "urban flood": HazardType.FLOOD,

    "drought": HazardType.DROUGHT,

    "dry spell": HazardType.DROUGHT,

    "water shortage": HazardType.DROUGHT,

    "cyclone": HazardType.CYCLONE,

    "cyclonic storm": HazardType.CYCLONE,

    "storm": HazardType.CYCLONE,

}

# ==========================================================
# HELPERS
# ==========================================================

def detect_input_file() -> Path:

    if INPUT_PARQUET.exists():
        return INPUT_PARQUET

    if INPUT_CSV.exists():
        return INPUT_CSV

    raise FileNotFoundError(
        "verified_events_final not found."
    )


def load_dataset(path: Path) -> pd.DataFrame:

    logger.info("Loading dataset")

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)

    elif path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)

    else:

        raise ValueError(
            f"Unsupported format: {path}"
        )

    if df.empty:

        raise ValueError(
            "Dataset is empty."
        )

    return df


def validate_columns(df: pd.DataFrame):

    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:

        raise ValueError(

            f"Missing required columns: {sorted(missing)}"

        )

    logger.info("Input schema validated")


def normalize_hazard(value: str) -> HazardType:

    if value is None:

        raise ValueError(
            "Missing hazard type."
        )

    key = value.strip().lower()

    if key not in HAZARD_MAP:

        raise ValueError(

            f"Unknown hazard type: {value}"

        )

    return HAZARD_MAP[key]


def optional_value(row, column):

    if column not in row:

        return None

    value = row[column]

    if pd.isna(value):

        return None

    return value
# ==========================================================
# ROW CONVERSION
# ==========================================================

def row_to_record(row) -> GroundTruthRecord:

    description = optional_value(row, "description")

    if not description:

        description = optional_value(row, "content")

    record = GroundTruthRecord(

        source=SourceType.NEWS,

        event_date=row["date"],

        state=row["state_query"],

        district=optional_value(row, "district"),

        hazard_type=normalize_hazard(
            row["event_type"]
        ),

        headline=row["headline"],

        description=description,

        source_name=row["source"],

        source_url=row["url"],

        latitude=optional_value(
            row,
            "latitude"
        ),

        longitude=optional_value(
            row,
            "longitude"
        ),

        fatalities=optional_value(
            row,
            "fatalities"
        ),

        injured=optional_value(
            row,
            "injured"
        ),

        displaced=optional_value(
            row,
            "displaced"
        ),

        affected_population=optional_value(
            row,
            "affected_population"
        ),

        economic_loss=optional_value(
            row,
            "economic_loss"
        ),

        verified=True,

    )

    return record


# ==========================================================
# PROCESS DATASET
# ==========================================================

def process_dataset(df):

    valid = []

    invalid = 0

    for index, row in df.iterrows():

        try:

            record = row_to_record(row)

            valid.append(
                record.model_dump()
            )

        except Exception as e:

            invalid += 1

            logger.warning(

                f"Row {index} skipped : {e}"

            )

    logger.info(

        f"Valid records : {len(valid)}"

    )

    logger.info(

        f"Invalid rows : {invalid}"

    )

    return valid, invalid


# ==========================================================
# WRITE PARQUET
# ==========================================================

def write_parquet(records):

    table = pa.Table.from_pylist(records)

    pq.write_table(

        table,

        OUTPUT_FILE,

        compression="snappy"

    )

    logger.info(

        f"Saved : {OUTPUT_FILE}"

    )
    # ==========================================================
# SUMMARY
# ==========================================================

def write_summary(

    input_file,

    rows_read,

    rows_written,

    rows_invalid,

    elapsed

):

    summary = {

        "collector": "collect_news_groundtruth",

        "version": "1.0",

        "input_file": str(input_file),

        "output_file": str(OUTPUT_FILE),

        "rows_read": rows_read,

        "rows_written": rows_written,

        "rows_invalid": rows_invalid,

        "execution_seconds": round(

            elapsed,

            2

        )

    }

    with open(

        SUMMARY_FILE,

        "w"

    ) as f:

        json.dump(

            summary,

            f,

            indent=4

        )

    logger.info(

        "Summary written."

    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    print()

    print("=" * 60)

    print(

        "Collect News Ground Truth"

    )

    print("=" * 60)

    start = time.time()

    input_file = detect_input_file()

    logger.info(

        f"Input : {input_file}"

    )

    df = load_dataset(

        input_file

    )

    validate_columns(df)

    records, invalid = process_dataset(df)

    write_parquet(records)

    elapsed = time.time() - start

    write_summary(

        input_file=input_file,

        rows_read=len(df),

        rows_written=len(records),

        rows_invalid=invalid,

        elapsed=elapsed

    )

    print()

    print("=" * 60)

    print("COLLECTION COMPLETE")

    print("=" * 60)

    print(

        f"Rows Read     : {len(df):,}"

    )

    print(

        f"Rows Written  : {len(records):,}"

    )

    print(

        f"Rows Invalid  : {invalid:,}"

    )

    print(

        f"Output        : {OUTPUT_FILE}"

    )

    print(

        f"Summary       : {SUMMARY_FILE}"

    )

    print(

        f"Time          : {elapsed:.2f}s"

    )

    print()


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    main()