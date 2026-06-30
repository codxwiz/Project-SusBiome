"""
============================================================
SusBiome
Build GDELT Candidate Events
Version : 1.0
============================================================

Purpose
-------
Convert parsed GDELT events into a candidate dataset
for later enrichment and disaster classification.

This module NEVER decides the final hazard type.

Output
------
data/silver/events/gdelt_candidate_events.parquet

============================================================
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
import hashlib
from datetime import datetime, UTC
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scripts.events.location_utils import (
    load_locations,
    searchable_text,
    infer_state,
    infer_district,
)

# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PARSED_EVENTS = (
    PROJECT_ROOT /
    "data/bronze/gdelt/parsed_events.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT /
    "data/silver/events"
)

OUTPUT_PARQUET = (
    OUTPUT_DIR /
    "gdelt_candidate_events.parquet"
)

OUTPUT_CSV = (
    OUTPUT_DIR /
    "gdelt_candidate_events.csv"
)

LOG_DIR = (
    PROJECT_ROOT /
    "data/bronze/gdelt/logs"
)

SUMMARY_JSON = (
    LOG_DIR /
    "build_candidate_events_summary.json"
)

LOG_FILE = (
    LOG_DIR /
    "build_candidate_events.log"
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

        description="Build GDELT candidate events"

    )

    parser.add_argument(

        "--min-score",

        type=int,

        default=20,

        help="Minimum candidate score"

    )

    parser.add_argument(

        "--csv",

        action="store_true",

        help="Also export CSV"

    )

    return parser.parse_args()

# ==========================================================
# REQUIRED INPUT SCHEMA
# ==========================================================

REQUIRED_COLUMNS = [

    "GLOBALEVENTID",
    "SQLDATE",

    "Actor1Name",
    "Actor2Name",

    "Actor1Geo_FullName",
    "Actor2Geo_FullName",

    "ActionGeo_FullName",
    "ActionGeo_CountryCode",

    "EventCode",
    "EventBaseCode",
    "EventRootCode",

    "QuadClass",

    "GoldsteinScale",

    "NumMentions",
    "NumSources",
    "NumArticles",

    "AvgTone",

    "SOURCEURL"

]

# ==========================================================
# OUTPUT SCHEMA
# ==========================================================

OUTPUT_COLUMNS = [

    # --------------------------------------------------
    # Identity
    # --------------------------------------------------

    "candidate_id",

    "gdelt_event_id",

    "event_date",

    # --------------------------------------------------
    # Location
    # --------------------------------------------------

    "country",

    "state",

    "district",

    "action_geo",

    "action_country",

    "action_lat",

    "action_lon",
    
    "action_adm1",

    "action_adm2",

    # --------------------------------------------------
    # Disaster Classification
    # --------------------------------------------------

    "event_type",

    "matched_keyword",

    "candidate_score",

    "geo_score",

    "disaster_score",

    "article_score",
    
    "gdelt_score",

    "candidate_reason",

    "needs_review",

    # --------------------------------------------------
    # GDELT Metadata
    # --------------------------------------------------

    "event_code",

    "event_base_code",

    "event_root_code",

    "quad_class",

    "goldstein_scale",

    "num_mentions",

    "num_sources",

    "num_articles",

    "avg_tone",

    # --------------------------------------------------
    # Actors
    # --------------------------------------------------

    "actor1",

    "actor2",

    # --------------------------------------------------
    # Text
    # --------------------------------------------------

    "headline",

    "description",

    # --------------------------------------------------
    # Provenance
    # --------------------------------------------------

    "source_url",

    "source_file",

    "created_at",

]

# ==========================================================
# NORTHEAST STATES
# ==========================================================

STATE_ALIASES = {

    "Arunachal Pradesh":[
        "arunachal",
        "itanagar"
    ],

    "Assam":[
        "assam",
        "guwahati",
        "gauhati",
        "brahmaputra"
    ],

    "Manipur":[
        "manipur",
        "imphal"
    ],

    "Meghalaya":[
        "meghalaya",
        "shillong",
        "cherrapunji"
    ],

    "Mizoram":[
        "mizoram",
        "aizawl"
    ],

    "Nagaland":[
        "nagaland",
        "kohima",
        "dimapur"
    ],

    "Sikkim":[
        "sikkim",
        "gangtok"
    ],

    "Tripura":[
        "tripura",
        "agartala"
    ]

}

# ==========================================================
# LOAD PARSED EVENTS
# ==========================================================

def load_dataset():

    if not PARSED_EVENTS.exists():

        raise FileNotFoundError(

            PARSED_EVENTS

        )

    df = pd.read_csv(

        PARSED_EVENTS,

        low_memory=False

    )

    logger.info(

        f"Loaded {len(df):,} parsed events."

    )

    return df

# ==========================================================
# VALIDATE INPUT
# ==========================================================

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

        "Input schema validated."

    )


# ==========================================================
# CANDIDATE SCORING
# ==========================================================

# ==========================================================
# GDELT DISASTER KEYWORDS
# ==========================================================

# GDELT EVENT CODE MAPPING
EVENT_CODE_HAZARDS = {
    # Flood / Water
    "0233": "FLOOD",
    "0234": "FLOOD",

    # Landslide
    "0231": "LANDSLIDE",

    # Cyclone / Storm
    "0232": "CYCLONE",

    # Drought
    "0235": "DROUGHT",

}


def detect_disaster(row):

    text = " ".join([

        str(row.get("Actor1Name", "")),

        str(row.get("Actor2Name", "")),

        str(row.get("ActionGeo_FullName", "")),

        str(row.get("SOURCEURL", ""))

    ]).lower()

    for event_type, keywords in DISASTER_KEYWORDS.items():

        for keyword in keywords:

            if keyword in text:

                return event_type, keyword

    event_code = str(row.get("EventCode", ""))

    if event_code in EVENT_CODE_HAZARDS:

        return (
            EVENT_CODE_HAZARDS[event_code],
            f"event_code:{event_code}"
        )

    return None, None

# ==========================================================
# GEOGRAPHY SCORE
# ==========================================================

def score_geography(row, state, district, state_hits):

    score = 0

    reasons = []

    if row.get("ActionGeo_CountryCode") == "IN":

        score += 20

        reasons.append("india")

    if state != "UNKNOWN":

        score += 30

        reasons.append("northeast_state")

    score += min(state_hits * 5, 15)

    if district != "UNKNOWN":

        score += 15

        reasons.append("district")

    if row.get("ActionGeo_Lat") not in ("", None):

        score += 5

    if row.get("ActionGeo_Long") not in ("", None):

        score += 5

    return min(score,100), reasons
# ==========================================================
# DISASTER SCORE
# ==========================================================

DISASTER_KEYWORDS = {

    "FLOOD": [

        "flood",
        "flooded",
        "flooding",
        "flash flood",
        "river flood",
        "overflow",
        "overflowed",
        "overflowing",
        "embankment",
        "breach",
        "waterlogging",
        "water logged",
        "inundation",
        "submerged",
        "washed away",
        "cloudburst",
        "heavy rainfall",
        "monsoon rain",
        "river burst"

    ],

    "DROUGHT": [

        "drought",
        "dry spell",
        "water shortage",
        "rainfall deficit",
        "crop failure",
        "crop loss",
        "low rainfall",
        "dry conditions"

    ],

    "CYCLONE": [

        "cyclone",
        "cyclonic storm",
        "storm surge",
        "landfall",
        "high winds",
        "strong winds",
        "tropical storm"

    ],

    "LANDSLIDE": [

        "landslide",
        "mudslide",
        "rockfall",
        "hill collapse",
        "slope failure",
        "debris flow"

    ],

    "HEATWAVE": [

        "heatwave",
        "heat wave",
        "extreme heat",
        "heat stroke"

    ],

    "COLD_WAVE": [

        "cold wave",
        "coldwave",
        "cold spell",
        "freezing temperatures"

    ]

}
HAZARD_PRIORITY = [

    "FLOOD",

    "LANDSLIDE",

    "CYCLONE",

    "DROUGHT",

    "HEATWAVE",

    "COLD_WAVE"

]


def score_disaster(row):

    text = " ".join([

        str(row.get("Actor1Name","")),

        str(row.get("Actor2Name","")),

        str(row.get("ActionGeo_FullName","")),

        str(row.get("SOURCEURL",""))

    ]).lower()

    score = 0

    reasons = []

    event_type = None

    keyword = None

    for hazard, words in DISASTER_KEYWORDS.items():

        for w in words:

            if w in text:

                score += 40

                event_type = hazard

                keyword = w

                reasons.append(f"keyword:{w}")

                return score,event_type,keyword,reasons

    return score,event_type,keyword,reasons

# ==========================================================
# ARTICLE SCORE
# ==========================================================

def score_article(row):

    score = 0

    reasons = []

    # Placeholder

    return score, reasons

# ==========================================================
# GDELT SCORE
# ==========================================================

def score_gdelt(row):

    score = 0

    reasons = []

    mentions = pd.to_numeric(
        row.get("NumMentions"),
        errors="coerce",
    )

    if pd.notna(mentions):

        if mentions >= 20:

            score += 5
            reasons.append("many_mentions")

        elif mentions >= 5:

            score += 2
            reasons.append("mentions")

    articles = pd.to_numeric(
        row.get("NumArticles"),
        errors="coerce",
    )

    if pd.notna(articles):

        if articles >= 10:

            score += 5
            reasons.append("many_articles")

        elif articles >= 3:

            score += 2
            reasons.append("articles")

    tone = pd.to_numeric(
        row.get("AvgTone"),
        errors="coerce",
    )

    if pd.notna(tone):

        if tone < -3:

            score += 5
            reasons.append("negative_tone")

    return score, reasons

# ==========================================================
# CANDIDATE SCORE
# ==========================================================

def score_candidate(row, state, district, state_hits):

    # --------------------------------------------------
    # Geography
    # --------------------------------------------------

    geo_score, geo_reasons = score_geography(

        row,

        state,

        district,

        state_hits

    )

    # --------------------------------------------------
    # Disaster
    # --------------------------------------------------

    (
        disaster_score,
        event_type,
        matched_keyword,
        disaster_reasons,

    ) = score_disaster(row)

    # --------------------------------------------------
    # Article
    # --------------------------------------------------

    article_score, article_reasons = score_article(

        row

    )

    # --------------------------------------------------
    # GDELT
    # --------------------------------------------------

    gdelt_score, gdelt_reasons = score_gdelt(

        row

    )

    # --------------------------------------------------
    # Final Score
    # --------------------------------------------------

    total_score = (

        geo_score +

        disaster_score +

        article_score +

        gdelt_score

    )

    total_score = min(

        total_score,

        100

    )

    # --------------------------------------------------
    # Reasons
    # --------------------------------------------------

    reasons = (

        geo_reasons +

        disaster_reasons +

        article_reasons +

        gdelt_reasons

    )

    return (

        total_score,

        reasons,

        geo_score,

        disaster_score,

        article_score,

        gdelt_score,

        event_type,

        matched_keyword

    )


# ==========================================================
# REVIEW DECISION
# ==========================================================

def needs_review(

    score,

    district

):

    if score < 60:

        return True

    if district == "UNKNOWN":

        return True

    return False


# ==========================================================
# BUILD ONE CANDIDATE
# ==========================================================

# ==========================================================
# BUILD STABLE CANDIDATE ID
# ==========================================================

def build_candidate_id(row):

    key = "|".join([

        str(row.get("GLOBALEVENTID", "")),

        str(row.get("SQLDATE", "")),

        str(row.get("ActionGeo_FullName", "")),

        str(row.get("SOURCEURL", ""))

    ])

    digest = hashlib.sha256(
        key.encode("utf-8")
    ).hexdigest()[:16]

    return f"CAND_{digest}"

def build_candidate(
    row,
    locations,
    min_score
):

    text = searchable_text(row)

    state, hits = infer_state(text)

    district = infer_district(
        text,
        state,
        locations
    )

    (
    score,
    reasons,
    geo_score,
    disaster_score,
    article_score,
    gdelt_score,
    event_type,
    matched_keyword,
) = score_candidate(

    row,

    state,

    district,

    hits

)

    if score < min_score:
        return None

    candidate = {

    # --------------------------------------------------
    # Identity
    # --------------------------------------------------

    "candidate_id":

        build_candidate_id(row),

    "gdelt_event_id":

        row.get("GLOBALEVENTID"),

    "event_date":

        row.get("SQLDATE"),

    # --------------------------------------------------
    # Geography
    # --------------------------------------------------

    "country":

        "India",

    "state":

        state,

    "district":

        district,

    "action_geo":

        row.get("ActionGeo_FullName"),

    "action_country":

        row.get("ActionGeo_CountryCode"),

    "action_lat":

        row.get("ActionGeo_Lat"),

    "action_lon":

        row.get("ActionGeo_Long"),

        "action_adm1":

        row.get("ActionGeo_ADM1Code"),

    "action_adm2":

        row.get("ActionGeo_ADM2Code"),

    # --------------------------------------------------
    # Classification
    # --------------------------------------------------

    "event_type":

        event_type,

    "matched_keyword":

        matched_keyword,

    "candidate_score":

        score,

    "geo_score":

        geo_score,

    "disaster_score":

        disaster_score,

    "article_score":

        article_score,

    "gdelt_score":

        gdelt_score,

    "candidate_reason":

        ";".join(reasons),

    "needs_review":

        needs_review(
            score,
            district
        ),

    # --------------------------------------------------
    # Event Metadata
    # --------------------------------------------------

    "event_code":

        row.get("EventCode"),

    "event_base_code":

        row.get("EventBaseCode"),

    "event_root_code":

        row.get("EventRootCode"),

    "quad_class":

        row.get("QuadClass"),

    "goldstein_scale":

        row.get("GoldsteinScale"),

    "num_mentions":

        row.get("NumMentions"),

    "num_sources":

        row.get("NumSources"),

    "num_articles":

        row.get("NumArticles"),

    "avg_tone":

        row.get("AvgTone"),

    # --------------------------------------------------
    # Actors
    # --------------------------------------------------

    "actor1":

        row.get("Actor1Name"),

    "actor2":

        row.get("Actor2Name"),

    # --------------------------------------------------
    # Text
    # --------------------------------------------------

    "headline":

        row.get("Headline", None),

    "description":

        row.get("Description", None),

    # --------------------------------------------------
    # Provenance
    # --------------------------------------------------

    "source_url":

        row.get("SOURCEURL"),

    "source_file":

        row.get("source_file"),

    "created_at":

        datetime.now(UTC).isoformat()

}

    return candidate


# ==========================================================
# BUILD DATASET
# ==========================================================

def build_candidates(

    df,

    min_score

):

    locations = load_locations()

    rows = []

    for _, row in df.iterrows():

        candidate = build_candidate(

            row,

            locations,

            min_score

        )

        if candidate is not None:

            rows.append(candidate)

    # ----------------------------------------------
    # Build DataFrame
    # ----------------------------------------------

    out = pd.DataFrame(

        rows,

        columns=OUTPUT_COLUMNS

    )

    # ----------------------------------------------
    # Remove duplicate candidates
    # ----------------------------------------------

    before = len(out)

    out = out.drop_duplicates(

        subset=[

            "candidate_id"

        ],

        keep="first"

    )

    removed = before - len(out)

    logger.info(

        f"Removed {removed:,} duplicate candidates."

    )

    logger.info(

        f"Candidates built: {len(out):,}"

    )

    return out
# ==========================================================
# WRITE DATASET
# ==========================================================

def write_outputs(

    df,

    export_csv=False

):

    if df.empty:

        logger.warning(

            "No candidate events produced."

        )

        return

    table = pa.Table.from_pandas(

        df,

        preserve_index=False

    )

    pq.write_table(

        table,

        OUTPUT_PARQUET,

        compression="snappy"

    )

    logger.info(

        f"Parquet written: {OUTPUT_PARQUET}"

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

    summary = {

        "created_at":

            datetime.now(UTC)

            .isoformat(),

        "rows":

            int(len(df)),

        "needs_review":

            int(

                df["needs_review"].sum()

            )

            if not df.empty else 0,

        "average_score":

            round(

                float(

                    df["candidate_score"]

                    .mean()

                ),

                2

            )

            if not df.empty else 0,

        "states":

            (

                df["state"]

                .value_counts()

                .to_dict()

            )

            if not df.empty else {},

    }

    return summary


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

            np.float64,

            np.float32

        )

    ):

        return float(obj)

    return obj


def write_summary(summary):

    summary = make_json_safe(summary)

    with open(

        SUMMARY_JSON,

        "w",

        encoding="utf-8"

    ) as f:

        json.dump(

            summary,

            f,

            indent=4

        )

    logger.info(

        f"Summary written: {SUMMARY_JSON}"

    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    args = parse_args()

    start = datetime.now(UTC)

    print()

    print("=" * 60)

    print("BUILD GDELT CANDIDATE EVENTS")

    print("=" * 60)

    try:

        df = load_dataset()

        validate_schema(df)

        candidates = build_candidates(

            df,

            args.min_score

        )

        write_outputs(

            candidates,

            export_csv=args.csv

        )

        summary = build_summary(

            candidates

        )

        write_summary(

            summary

        )

        elapsed = (datetime.now(UTC) - start).total_seconds()

        print()

        print("=" * 60)

        print("BUILD COMPLETE")

        print("=" * 60)

        print(

            f"Candidates : {len(candidates):,}"

        )

        print(

            f"Parquet   : {OUTPUT_PARQUET}"

        )

        if args.csv:

            print(

                f"CSV       : {OUTPUT_CSV}"

            )

        print(

            f"Summary   : {SUMMARY_JSON}"

        )

        print(

            f"Elapsed   : {elapsed:.2f}s"

        )

        print()

        sys.exit(0)

    except Exception as exc:

        logger.exception(exc)

        print()

        print("=" *60)

        print("BUILD FAILED")

        print("=" *60)

        print(exc)

        print()

        sys.exit(1)


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    main()