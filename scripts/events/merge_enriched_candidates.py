"""
============================================================
SusBiome
Merge Enriched GDELT Candidates
Version : 1.0
============================================================

Purpose
-------
Merge the base candidate dataset with the article
enrichment dataset.

This script produces the final candidate dataset used
by classify_gdelt_candidates.py.

Pipeline

Candidate Events
        +
Enriched Articles

↓

Merged Candidate Events

Author
------
SusBiome
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CANDIDATE_INPUT = (
    PROJECT_ROOT
    / "data/silver/events/gdelt_candidate_events.parquet"
)

ENRICHED_INPUT = (
    PROJECT_ROOT
    / "data/silver/events/gdelt_enriched_candidates.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data/silver/events"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "gdelt_candidate_events_enriched.parquet"
)

OUTPUT_CSV = (
    OUTPUT_DIR
    / "gdelt_candidate_events_enriched.csv"
)

LOG_DIR = (
    PROJECT_ROOT
    / "data/bronze/gdelt/logs"
)

SUMMARY_FILE = (
    LOG_DIR
    / "gdelt_candidate_events_enriched_summary.json"
)

LOG_FILE = (
    LOG_DIR
    / "gdelt_candidate_events_enriched.log"
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

        logging.StreamHandler(sys.stdout)

    ]

)

logger = logging.getLogger(__name__)
# ==========================================================
# CLI
# ==========================================================

def parse_args():

    parser = argparse.ArgumentParser(

        description="Merge enriched GDELT candidates"

    )

    parser.add_argument(

        "--csv",

        action="store_true",

        help="Also export CSV"

    )

    return parser.parse_args()
# ==========================================================
# LOAD DATASETS
# ==========================================================

def load_candidates():

    if not CANDIDATE_INPUT.exists():

        raise FileNotFoundError(

            CANDIDATE_INPUT

        )

    df = pd.read_parquet(

        CANDIDATE_INPUT

    )

    logger.info(

        f"Loaded {len(df):,} candidates."

    )

    return df


def load_enrichment():

    if not ENRICHED_INPUT.exists():

        raise FileNotFoundError(

            ENRICHED_INPUT

        )

    df = pd.read_parquet(

        ENRICHED_INPUT

    )

    logger.info(

        f"Loaded {len(df):,} enriched rows."

    )

    return df
# ==========================================================
# VALIDATION
# ==========================================================

def validate_inputs(

    candidates,

    enriched,

):

    if "candidate_id" not in candidates.columns:

        raise ValueError(

            "candidate_id missing from candidates"

        )

    if "candidate_id" not in enriched.columns:

        raise ValueError(

            "candidate_id missing from enrichment"

        )

    logger.info(

        "Input validation successful."

    )
    # ==========================================================
# MERGE DATASETS
# ==========================================================

ENRICHMENT_COLUMNS = [

    "candidate_id",

    "article_title",
    "article_description",
    "article_text",

    "article_length",

    "article_quality",

    "enrichment_confidence",

    "location_mentions",

    "disaster_keywords"

]


def merge_datasets(

    candidates,

    enriched,

):

    # ----------------------------------------------
    # Keep only enrichment columns
    # ----------------------------------------------

    available = [

        c

        for c in ENRICHMENT_COLUMNS

        if c in enriched.columns

    ]

    enrichment = enriched[

        available

    ].copy()

    # ----------------------------------------------
    # Remove duplicate candidate IDs
    # ----------------------------------------------

    enrichment = enrichment.drop_duplicates(

        subset=[

            "candidate_id"

        ],

        keep="first"

    )

    logger.info(

        f"Unique enrichment rows : {len(enrichment):,}"

    )

    # ----------------------------------------------
    # Merge
    # ----------------------------------------------

    merged = candidates.merge(

        enrichment,

        on="candidate_id",

        how="left",

        validate="one_to_one"

    )

    logger.info(

        f"Merged rows : {len(merged):,}"

    )

    return merged
# ==========================================================
# MERGE DIAGNOSTICS
# ==========================================================

def diagnostics(df):

    logger.info("")

    logger.info("Merge Diagnostics")

    logger.info("---------------------------")

    logger.info(

        f"Rows : {len(df):,}"

    )

    logger.info(

        f"Unique Candidate IDs : "

        f"{df['candidate_id'].nunique():,}"

    )

    logger.info(

        f"Duplicate Candidate IDs : "

        f"{df.duplicated('candidate_id').sum():,}"

    )

    logger.info("")

    diagnostics_columns = [

        "article_title",

        "article_text",

        "article_quality",

        "enrichment_confidence",

        "disaster_keywords"

    ]

    for column in diagnostics_columns:

        if column not in df.columns:

            continue

        populated = (

            df[column]

            .notna()

            .sum()

        )

        logger.info(

            f"{column:<28}"

            f"{populated:>6,}"

        )
        # ==========================================================
# BUILD SUMMARY
# ==========================================================

def build_summary(df):

    return {

        "created_at":

            datetime.now(

                UTC

            ).isoformat(),

        "rows":

            int(

                len(df)

            ),

        "unique_candidates":

            int(

                df["candidate_id"]

                .nunique()

            ),

        "article_titles":

            int(

                df["article_title"]

                .notna()

                .sum()

            )

            if "article_title" in df.columns

            else 0,

        "article_text":

            int(

                df["article_text"]

                .notna()

                .sum()

            )

            if "article_text" in df.columns

            else 0,

        "keywords":

            int(

                df["disaster_keywords"]

                .notna()

                .sum()

            )

            if "disaster_keywords" in df.columns

            else 0

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
# WRITE OUTPUT
# ==========================================================

def write_output(

    df,

    export_csv=False,

):

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

    print("MERGE ENRICHED GDELT CANDIDATES")

    print("=" * 60)

    candidates = load_candidates()

    enriched = load_enrichment()

    validate_inputs(

        candidates,

        enriched,

    )

    merged = merge_datasets(

        candidates,

        enriched,

    )

    diagnostics(

        merged

    )

    write_output(

        merged,

        args.csv,

    )

    summary = build_summary(

        merged

    )

    write_summary(

        summary

    )

    elapsed = (

        datetime.now(UTC)

        -

        start

    ).total_seconds()

    print()

    print("=" * 60)

    print("MERGE COMPLETE")

    print("=" * 60)

    print(

        f"Rows      : {len(merged):,}"

    )

    print(

        f"Parquet   : {OUTPUT_FILE}"

    )

    if args.csv:

        print(

            f"CSV       : {OUTPUT_CSV}"

        )

    print(

        f"Summary   : {SUMMARY_FILE}"

    )

    print(

        f"Elapsed   : {elapsed:.2f}s"

    )

    print()
   
    # ==========================================================
    # ENTRY POINT
    # ==========================================================

if __name__ == "__main__":

    main()