from pathlib import Path
import pandas as pd

# ==========================================================
# PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FILE = (
    PROJECT_ROOT /
    "data/bronze/gdelt/india/20150501000000.export.CSV"
)

# ==========================================================
# OFFICIAL GDELT EVENT COLUMN NAMES (61 Columns)
# ==========================================================

COLUMNS = [
    "GLOBALEVENTID",
    "SQLDATE",
    "MonthYear",
    "Year",
    "FractionDate",
    "Actor1Code",
    "Actor1Name",
    "Actor1CountryCode",
    "Actor1KnownGroupCode",
    "Actor1EthnicCode",
    "Actor1Religion1Code",
    "Actor1Religion2Code",
    "Actor1Type1Code",
    "Actor1Type2Code",
    "Actor1Type3Code",
    "Actor2Code",
    "Actor2Name",
    "Actor2CountryCode",
    "Actor2KnownGroupCode",
    "Actor2EthnicCode",
    "Actor2Religion1Code",
    "Actor2Religion2Code",
    "Actor2Type1Code",
    "Actor2Type2Code",
    "Actor2Type3Code",
    "IsRootEvent",
    "EventCode",
    "EventBaseCode",
    "EventRootCode",
    "QuadClass",
    "GoldsteinScale",
    "NumMentions",
    "NumSources",
    "NumArticles",
    "AvgTone",
    "Actor1Geo_Type",
    "Actor1Geo_FullName",
    "Actor1Geo_CountryCode",
    "Actor1Geo_ADM1Code",
    "Actor1Geo_Lat",
    "Actor1Geo_Long",
    "Actor1Geo_FeatureID",
    "Actor2Geo_Type",
    "Actor2Geo_FullName",
    "Actor2Geo_CountryCode",
    "Actor2Geo_ADM1Code",
    "Actor2Geo_Lat",
    "Actor2Geo_Long",
    "Actor2Geo_FeatureID",
    "ActionGeo_Type",
    "ActionGeo_FullName",
    "ActionGeo_CountryCode",
    "ActionGeo_ADM1Code",
    "ActionGeo_Lat",
    "ActionGeo_Long",
    "ActionGeo_FeatureID",
    "DATEADDED",
    "SOURCEURL"
]

# ==========================================================
# LOAD
# ==========================================================

print("=" * 70)
print("Loading GDELT Event File")
print("=" * 70)

df = pd.read_csv(
    FILE,
    header=None,
    names=COLUMNS,
    low_memory=False
)

print(f"Rows    : {len(df):,}")
print(f"Columns : {len(df.columns)}")

# ----------------------------------------------------------
# Remove accidental header row if present
# ----------------------------------------------------------

df = df[df["GLOBALEVENTID"] != "0"]

# ==========================================================
# BASIC INFO
# ==========================================================

print("\nSample Records\n")

print(df[[
    "SQLDATE",
    "EventCode",
    "EventRootCode",
    "Actor1CountryCode",
    "Actor2CountryCode",
    "ActionGeo_CountryCode",
    "ActionGeo_FullName",
    "ActionGeo_Lat",
    "ActionGeo_Long",
    "SOURCEURL"
]].head(10))

# ==========================================================
# UNIQUE COUNTRY CODES
# ==========================================================

print("\nUnique Action Countries")

print(
    df["ActionGeo_CountryCode"]
    .dropna()
    .value_counts()
    .head(30)
)

# ==========================================================
# EVENT CODES
# ==========================================================

print("\nTop Event Codes")

print(
    df["EventRootCode"]
    .value_counts()
    .head(30)
)

# ==========================================================
# INDIA EVENTS
# ==========================================================

india = df[
    df["ActionGeo_CountryCode"] == "IN"
]

print("\n" + "=" * 70)
print("INDIA EVENTS")
print("=" * 70)

print(f"India Events : {len(india)}")

if len(india):

    print(india[[
        "SQLDATE",
        "ActionGeo_FullName",
        "EventCode",
        "EventRootCode",
        "SOURCEURL"
    ]].head(20))

# ==========================================================
# SAVE INDIA SAMPLE
# ==========================================================

OUT = (
    PROJECT_ROOT /
    "data/bronze/gdelt/india_sample.csv"
)

india.to_csv(
    OUT,
    index=False
)

print("\nSaved sample to")

print(OUT)