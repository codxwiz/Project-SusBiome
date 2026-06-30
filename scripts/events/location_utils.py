"""
============================================================
SusBiome
Location Utilities
============================================================

Shared location inference utilities.

Used by:

- gdelt_pipeline.py
- build_candidate_events.py
- future IMD collectors
- news collectors
- ground truth builders

============================================================
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# ==========================================================
# PROJECT ROOT
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_LOCATIONS = (
    PROJECT_ROOT /
    "data/raw/locations.csv"
)

# ==========================================================
# STATE ALIASES
# ==========================================================

STATE_ALIASES = {

    "Arunachal Pradesh": [
        "arunachal pradesh",
        "arunachal",
        "itanagar",
    ],

    "Assam": [
        "assam",
        "guwahati",
        "gauhati",
        "brahmaputra",
        "barak valley",
    ],

    "Manipur": [
        "manipur",
        "imphal",
    ],

    "Meghalaya": [
        "meghalaya",
        "shillong",
        "cherrapunji",
        "sohra",
        "mawsynram",
    ],

    "Mizoram": [
        "mizoram",
        "aizawl",
    ],

    "Nagaland": [
        "nagaland",
        "kohima",
        "dimapur",
    ],

    "Sikkim": [
        "sikkim",
        "gangtok",
    ],

    "Tripura": [
        "tripura",
        "agartala",
    ]

}

# ==========================================================
# NORMALIZATION
# ==========================================================

def normalize_text(value):

    if pd.isna(value):

        return ""

    text = str(value).lower()

    text = re.sub(

        r"https?://",

        " ",

        text

    )

    text = re.sub(

        r"[^a-z0-9]+",

        " ",

        text

    )

    return re.sub(

        r"\s+",

        " ",

        text

    ).strip()

# ==========================================================
# PHRASE MATCH
# ==========================================================

def contains_phrase(

    text,

    phrase

):

    text = normalize_text(text)

    phrase = normalize_text(phrase)

    if not phrase:

        return False

    return re.search(

        rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])",

        text

    ) is not None

# ==========================================================
# LOAD LOCATIONS
# ==========================================================

def load_locations(

    path=DEFAULT_LOCATIONS

):

    if not Path(path).exists():

        return pd.DataFrame(

            columns=[

                "state",

                "district"

            ]

        )

    df = pd.read_csv(path)

    required = {

        "state",

        "district"

    }

    missing = required - set(df.columns)

    if missing:

        raise ValueError(

            f"Missing columns: {missing}"

        )

    df["state_norm"] = (

        df["state"]

        .map(normalize_text)

    )

    df["district_norm"] = (

        df["district"]

        .map(normalize_text)

    )

    return df

# ==========================================================
# SEARCHABLE TEXT
# ==========================================================

def searchable_text(

    row

):

    fields = [

        "Actor1Name",

        "Actor2Name",

        "Actor1Geo_FullName",

        "Actor2Geo_FullName",

        "ActionGeo_FullName",

        "SOURCEURL",

    ]

    text = []

    for field in fields:

        value = row.get(

            field,

            ""

        )

        if pd.notna(value):

            text.append(

                str(value)

            )

    return normalize_text(

        " ".join(text)

    )

# ==========================================================
# STATE INFERENCE
# ==========================================================

def infer_state(

    text

):

    matches = []

    for state, aliases in STATE_ALIASES.items():

        hits = sum(

            1

            for alias in aliases

            if contains_phrase(

                text,

                alias

            )

        )

        if hits:

            matches.append(

                (

                    state,

                    hits

                )

            )

    if not matches:

        return (

            "UNKNOWN",

            0

        )

    matches.sort(

        key=lambda x: x[1],

        reverse=True

    )

    return matches[0]

# ==========================================================
# DISTRICT INFERENCE
# ==========================================================

def infer_district(

    text,

    state,

    locations

):

    if state == "UNKNOWN":

        return "UNKNOWN"

    subset = locations[

        locations["state"]

        .str.lower()

        == state.lower()

    ]

    best = "UNKNOWN"

    longest = 0

    for _, row in subset.iterrows():

        district = row["district"]

        district_norm = row["district_norm"]

        if (

            district_norm

            and contains_phrase(

                text,

                district_norm

            )

        ):

            if len(

                district_norm

            ) > longest:

                longest = len(

                    district_norm

                )

                best = district

    return best