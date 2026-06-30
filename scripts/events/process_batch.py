from pathlib import Path
import pandas as pd
import shutil

# ==========================================================
# PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = PROJECT_ROOT / "data/bronze/gdelt/extracted"

OUTPUT_DIR = PROJECT_ROOT / "data/bronze/gdelt/india"

LOG_DIR = PROJECT_ROOT / "data/bronze/gdelt/logs"

DONE_DIR = PROJECT_ROOT / "data/bronze/gdelt/processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
DONE_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# GDELT SCHEMA
# ==========================================================

COLUMNS = [
"GLOBALEVENTID","SQLDATE","MonthYear","Year","FractionDate",
"Actor1Code","Actor1Name","Actor1CountryCode",
"Actor1KnownGroupCode","Actor1EthnicCode",
"Actor1Religion1Code","Actor1Religion2Code",
"Actor1Type1Code","Actor1Type2Code","Actor1Type3Code",
"Actor2Code","Actor2Name","Actor2CountryCode",
"Actor2KnownGroupCode","Actor2EthnicCode",
"Actor2Religion1Code","Actor2Religion2Code",
"Actor2Type1Code","Actor2Type2Code","Actor2Type3Code",
"IsRootEvent","EventCode","EventBaseCode",
"EventRootCode","QuadClass","GoldsteinScale",
"NumMentions","NumSources","NumArticles",
"AvgTone",
"Actor1Geo_Type","Actor1Geo_FullName",
"Actor1Geo_CountryCode","Actor1Geo_ADM1Code",
"Actor1Geo_Lat","Actor1Geo_Long",
"Actor1Geo_FeatureID",
"Actor2Geo_Type","Actor2Geo_FullName",
"Actor2Geo_CountryCode","Actor2Geo_ADM1Code",
"Actor2Geo_Lat","Actor2Geo_Long",
"Actor2Geo_FeatureID",
"ActionGeo_Type","ActionGeo_FullName",
"ActionGeo_CountryCode","ActionGeo_ADM1Code",
"ActionGeo_Lat","ActionGeo_Long",
"ActionGeo_FeatureID",
"DATEADDED",
"SOURCEURL"
]

# ==========================================================
# SEARCH TERMS
# ==========================================================

SEARCH_TERMS = [

"india",

"assam",

"arunachal",

"meghalaya",

"mizoram",

"nagaland",

"tripura",

"sikkim",

"manipur"

]

# ==========================================================
# PROCESS
# ==========================================================

files = sorted(INPUT_DIR.glob("*.CSV"))

print("="*60)
print(f"Files Found : {len(files)}")
print("="*60)

for file in files:

    print(file.name)

    try:

        df = pd.read_csv(
            file,
            header=None,
            names=COLUMNS,
            low_memory=False
        )

        # remove accidental header row if exists
        df = df[df["GLOBALEVENTID"]!="0"]

        location = (
            df["ActionGeo_FullName"]
            .fillna("")
            .str.lower()
        )

        mask = False

        for term in SEARCH_TERMS:

            mask = mask | location.str.contains(
                term,
                regex=False
            )

        india = df[mask]

        output = OUTPUT_DIR / (
            file.stem + ".parquet"
        )

        india.to_parquet(
            output,
            index=False
        )

        shutil.move(
            file,
            DONE_DIR / file.name
        )

        print(
            f"Saved {len(india)} rows"
        )

    except Exception as e:

        print(e)

print("\nBatch complete.")