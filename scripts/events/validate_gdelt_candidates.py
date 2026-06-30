"""
============================================================
SusBiome
GDELT Candidate Validator
Version : 1.0
============================================================

Modes
-----

default
    Validate gdelt_disaster_candidates.csv

--parsed
    Validate parsed GDELT events

--compare
    Compare parsed events against candidate events

============================================================
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SILVER_DIR = PROJECT_ROOT / "data/silver/events"

BRONZE_DIR = PROJECT_ROOT / "data/bronze/gdelt"

LOG_DIR = BRONZE_DIR / "logs"

SAMPLE_DIR = LOG_DIR / "samples"

LOG_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATE_FILE = (
    SILVER_DIR /
    "gdelt_disaster_candidates.csv"
)

PARSED_FILE = (
    BRONZE_DIR /
    "parsed_events.csv"
)

SUMMARY_JSON = (
    LOG_DIR /
    "gdelt_validation_report.json"
)

LOG_FILE = (
    LOG_DIR /
    "validate_gdelt_candidates.log"
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

        description="Validate GDELT pipeline"

    )

    parser.add_argument(

        "--parsed",

        action="store_true",

        help="Validate parsed events"

    )

    parser.add_argument(

        "--compare",

        action="store_true",

        help="Compare parsed vs candidates"

    )

    parser.add_argument(

        "--sample-size",

        type=int,

        default=25

    )

    return parser.parse_args()

# ==========================================================
# DATA LOADING
# ==========================================================

def load_csv(path: Path):

    if not path.exists():

        raise FileNotFoundError(path)

    df = pd.read_csv(path)

    logger.info(

        f"Loaded {len(df):,} rows"

    )

    return df

# ==========================================================
# VALIDATION
# ==========================================================

REQUIRED_COLUMNS = [

    "date",

    "state",

    "district",

    "event_type",

    "confidence_score",

    "needs_review",

    "gdelt_event_id",

    "event_code",

    "event_root_code",

    "action_geo",

    "action_country",

    "action_lat",

    "action_lon",

    "source_url"

]

def validate_schema(df):

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

        "Schema validation passed."

    )

# ==========================================================
# BASIC METRICS
# ==========================================================

def basic_metrics(df):

    metrics = {}

    metrics["rows"] = len(df)

    metrics["duplicates"] = (

        df["gdelt_event_id"]

        .duplicated()

        .sum()

    )

    metrics["missing_state"] = (

        df["state"]

        .isna()

        .sum()

    )

    metrics["missing_district"] = (

        df["district"]

        .isna()

        .sum()

    )

    metrics["missing_url"] = (

        df["source_url"]

        .isna()

        .sum()

    )

    metrics["needs_review"] = int(

        df["needs_review"]

        .sum()

    )

    return metrics

# ==========================================================
# DISTRIBUTIONS
# ==========================================================

def value_counts(df, column):

    if column not in df.columns:

        return {}

    return (

        df[column]

        .fillna("UNKNOWN")

        .value_counts()

        .to_dict()

    )
# ==========================================================
# INDIA / NORTHEAST ANALYSIS
# ==========================================================

NORTHEAST_STATES = [

    "Arunachal Pradesh",
    "Assam",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Sikkim",
    "Tripura"

]

def regional_metrics(df):

    metrics = {}

    if "state" not in df.columns:

        metrics["india_rows"] = 0
        metrics["northeast_rows"] = 0
        metrics["state_distribution"] = {}

        return metrics

    india = df[
        df["state"]
        .notna()
    ]

    northeast = india[
        india["state"]
        .isin(NORTHEAST_STATES)
    ]

    metrics["india_rows"] = len(india)

    metrics["northeast_rows"] = len(northeast)

    metrics["state_distribution"] = (

        northeast["state"]

        .value_counts()

        .to_dict()

    )

    return metrics

# ==========================================================
# HAZARD ANALYSIS
# ==========================================================

def hazard_metrics(df):

    metrics = {}

    if "event_type" not in df.columns:

        metrics["hazards"] = {}

        return metrics

    metrics["hazards"] = (

        df["event_type"]

        .fillna("UNKNOWN")

        .value_counts()

        .to_dict()

    )

    return metrics

# ==========================================================
# CONFIDENCE ANALYSIS
# ==========================================================

def confidence_metrics(df):

    metrics = {}

    if "confidence_score" not in df.columns:

        return metrics

    score = pd.to_numeric(

        df["confidence_score"],

        errors="coerce"

    )

    metrics["90_plus"] = int(

        (score >= 90).sum()

    )

    metrics["70_89"] = int(

        ((score >= 70) & (score < 90)).sum()

    )

    metrics["50_69"] = int(

        ((score >= 50) & (score < 70)).sum()

    )

    metrics["below_50"] = int(

        (score < 50).sum()

    )

    metrics["average"] = round(

        float(score.mean()),

        2

    ) if len(score.dropna()) else 0

    return metrics

# ==========================================================
# SAMPLE EXPORTS
# ==========================================================

def export_sample(

    df,

    filename,

    sample_size

):

    if len(df) == 0:

        return

    output = SAMPLE_DIR / filename

    df.head(sample_size).to_csv(

        output,

        index=False

    )

    logger.info(

        f"Sample written: {output.name}"

    )

# ==========================================================
# REJECTION ANALYSIS
# ==========================================================

def rejection_metrics(df):

    metrics = {}

    rejected = df[

        df["needs_review"] == True

    ].copy()

    metrics["rejected"] = len(rejected)

    if len(rejected):

        metrics["reasons"] = (

            rejected["review_reason"]

            .fillna("UNKNOWN")

            .value_counts()

            .to_dict()

        )

    else:

        metrics["reasons"] = {}

    export_sample(

        rejected,

        "rejected_sample.csv",

        25

    )

    return metrics

# ==========================================================
# COMPARISON MODE
# ==========================================================

def compare_datasets(

    parsed,

    candidates

):

    comparison = {

        "parsed_rows": len(parsed),

        "candidate_rows": len(candidates),

        "lost_rows":

            len(parsed) -

            len(candidates)

    }

    if len(parsed):

        comparison["success_rate"] = round(

            len(candidates)

            / len(parsed)

            * 100,

            2

        )

    else:

        comparison["success_rate"] = 0

    return comparison

# ==========================================================
# JSON REPORT
# ==========================================================

# ==========================================================
# JSON REPORT
# ==========================================================

def make_json_safe(obj):

    import numpy as np

    if isinstance(obj, dict):

        return {
            k: make_json_safe(v)
            for k, v in obj.items()
        }

    if isinstance(obj, list):

        return [
            make_json_safe(v)
            for v in obj
        ]

    if isinstance(
        obj,
        (
            np.integer,
            np.int64,
            np.int32
        )
    ):

        return int(obj)

    if isinstance(
        obj,
        (
            np.floating,
            np.float32,
            np.float64
        )
    ):

        return float(obj)

    return obj


def write_report(report):

    report = make_json_safe(report)

    with open(
        SUMMARY_JSON,
        "w"
    ) as f:

        json.dump(
            report,
            f,
            indent=4
        )

    logger.info(
        f"JSON report saved: {SUMMARY_JSON}"
    )

# ==========================================================
# CONSOLE REPORT
# ==========================================================

def print_report(report):

    print()

    print("=" * 60)

    print("GDELT VALIDATION REPORT")

    print("=" * 60)

    for key, value in report.items():

        if isinstance(value, dict):

            continue

        print(

            f"{key:<25}{value}"

        )

    print()
    # ==========================================================
# CANDIDATE VALIDATION
# ==========================================================

def run_candidate_validation(sample_size=25):

    logger.info("Running candidate validation")

    df = load_csv(CANDIDATE_FILE)

    validate_schema(df)

    report = {}

    report["mode"] = "candidate"

    report.update(
        basic_metrics(df)
    )

    report.update(
        regional_metrics(df)
    )

    report.update(
        hazard_metrics(df)
    )

    report.update(
        confidence_metrics(df)
    )

    report.update(
        rejection_metrics(df)
    )

    export_sample(
        df,
        "candidate_sample.csv",
        sample_size
    )

    if "event_type" in df.columns:

        for hazard in [
            "flood",
            "drought",
            "cyclone"
        ]:

            sample = df[
                df["event_type"]
                .astype(str)
                .str.lower()
                == hazard
            ]

            export_sample(
                sample,
                f"{hazard}_sample.csv",
                sample_size
            )

    write_report(report)

    print_report(report)


# ==========================================================
# PARSED VALIDATION
# ==========================================================

def run_parsed_validation(sample_size=25):

    logger.info("Running parsed validation")

    parsed = load_csv(PARSED_FILE)

    report = {}

    report["mode"] = "parsed"

    report["rows"] = len(parsed)

    report["columns"] = len(parsed.columns)

    report["duplicates"] = parsed.duplicated().sum()

    export_sample(
        parsed,
        "parsed_sample.csv",
        sample_size
    )

    write_report(report)

    print_report(report)


# ==========================================================
# COMPARE VALIDATION
# ==========================================================

def run_compare_validation(sample_size=25):

    logger.info("Running comparison")

    parsed = load_csv(PARSED_FILE)

    candidates = load_csv(
        CANDIDATE_FILE
    )

    report = {}

    report["mode"] = "compare"

    report.update(

        compare_datasets(

            parsed,

            candidates

        )

    )

    report["parsed_columns"] = len(
        parsed.columns
    )

    report["candidate_columns"] = len(
        candidates.columns
    )

    export_sample(

        parsed,

        "parsed_compare_sample.csv",

        sample_size

    )

    export_sample(

        candidates,

        "candidate_compare_sample.csv",

        sample_size

    )

    write_report(report)

    print_report(report)


# ==========================================================
# MAIN
# ==========================================================

def main():

    start = time.time()

    args = parse_args()

    print()

    print("=" * 60)

    print("SusBiome GDELT Validator")

    print("=" * 60)

    try:

        if args.compare:

            run_compare_validation(
                args.sample_size
            )

        elif args.parsed:

            run_parsed_validation(
                args.sample_size
            )

        else:

            run_candidate_validation(
                args.sample_size
            )

        elapsed = round(
            time.time() - start,
            2
        )

        print()

        print("=" * 60)

        print("VALIDATION COMPLETE")

        print("=" * 60)

        print(f"Execution Time : {elapsed}s")

        print(f"Report         : {SUMMARY_JSON}")

        print(f"Logs           : {LOG_FILE}")

        print(f"Samples        : {SAMPLE_DIR}")

        print()

        sys.exit(0)

    except Exception as e:

        logger.exception(e)

        print()

        print("=" * 60)

        print("VALIDATION FAILED")

        print("=" * 60)

        print(e)

        print()

        sys.exit(1)


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    main()