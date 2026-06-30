import pyarrow.parquet as pq
import os
import tempfile
import duckdb
import pyarrow as pa
from pathlib import Path
import pandas as pd
import requests
import json
import time
import zipfile
import io

# ==========================================================
# CONFIG
# ==========================================================

FILES_PER_RUN = 25
TIMEOUT = 180
RETRIES = 3
CHUNK_SIZE = 1024 * 1024

# ==========================================================
# GDELT SCHEMA
# ==========================================================

GDELT_COLUMNS = [
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
# DUCKDB
# ==========================================================

con = duckdb.connect(database=":memory:")

# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

QUEUE_FILE = PROJECT_ROOT / "data/bronze/gdelt/index/download_queue.csv"

RAW_DIR = PROJECT_ROOT / "data/bronze/gdelt/raw"

CHECKPOINT_DIR = PROJECT_ROOT / "data/bronze/gdelt/checkpoint"

CHECKPOINT_FILE = CHECKPOINT_DIR / "checkpoint.json"
PARQUET_DIR = PROJECT_ROOT / "data/silver/events"

PARQUET_DIR.mkdir(parents=True, exist_ok=True)

PARQUET_FILE = PARQUET_DIR / "india_events.parquet"

RAW_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# LOAD CHECKPOINT
# ==========================================================

if CHECKPOINT_FILE.exists():

    with open(CHECKPOINT_FILE, "r") as f:
        checkpoint = json.load(f)

else:

    checkpoint = {
        "last_index": -1
    }

# ==========================================================
# LOAD DOWNLOAD QUEUE
# ==========================================================

queue = pd.read_csv(QUEUE_FILE)

start_index = checkpoint["last_index"] + 1

end_index = min(
    start_index + FILES_PER_RUN,
    len(queue)
)

print("=" * 70)
print("SUSBIOME GDELT PIPELINE")
print("=" * 70)

print(f"Queue Size      : {len(queue):,}")
print(f"Starting Index  : {start_index}")
print(f"Ending Index    : {end_index-1}")

print()

# ==========================================================
# DOWNLOAD LOOP
# ==========================================================

downloaded = 0
skipped = 0
failed = 0
processed = 0

for idx in range(start_index, end_index):

    row = queue.iloc[idx]

    filename = row["filename"]
    url = row["url"]

    destination = RAW_DIR / filename

    print("=" * 70)
    print(f"[{idx+1}/{len(queue):,}]")
    print(filename)

    # ------------------------------------------------------
    # Skip existing download
    # ------------------------------------------------------

    if destination.exists():

        print("Already downloaded")

    else:

        success = False

        for attempt in range(RETRIES):

            try:

                response = requests.get(
                    url,
                    timeout=TIMEOUT,
                    stream=True
                )

                response.raise_for_status()

                with open(destination, "wb") as out:

                    for chunk in response.iter_content(CHUNK_SIZE):

                        if chunk:
                            out.write(chunk)

                success = True
                downloaded += 1

                print("✓ Downloaded")

                break

            except Exception as e:

                print(f"Retry {attempt+1}/{RETRIES}")

                if attempt == RETRIES - 1:

                    print(e)

                time.sleep(2)

        if not success:

            failed += 1
            continue

    # ======================================================
    # STAGE 2
    # Extract ZIP into memory
    # ======================================================

    try:

        with zipfile.ZipFile(destination, "r") as archive:

            members = archive.namelist()

            if len(members) != 1:

                raise Exception(
                    f"Unexpected ZIP contents: {members}"
                )

            csv_name = members[0]

            with archive.open(csv_name) as csv_file:

                csv_bytes = csv_file.read()

        print(f"✓ Extracted to Memory")
        print(f"CSV File : {csv_name}")
        print(f"Size     : {len(csv_bytes):,} bytes")
        # ======================================================
    except Exception as e:

        failed += 1

        print("Stage 2 Error")
        print(e)

        continue

    # STAGE 3 + STAGE 4
    # DuckDB -> Filter -> Parquet
    # ======================================================

    try:

        # --------------------------------------------------
        # Save memory buffer temporarily
        # --------------------------------------------------

        with tempfile.NamedTemporaryFile(
            suffix=".csv",
            delete=False
        ) as tmp:

            tmp.write(csv_bytes)
            temp_csv = tmp.name

        # --------------------------------------------------
        # Read CSV with DuckDB
        # --------------------------------------------------

        con.execute(f"""
        CREATE OR REPLACE TABLE gdelt AS

        SELECT *

        FROM read_csv(
    '{temp_csv}',
    delim = '\t',
    header = FALSE,
    auto_detect = FALSE,
    ignore_errors = TRUE,
    all_varchar = TRUE
)
        """)

        # --------------------------------------------------
        # Check schema
        # --------------------------------------------------

        cols = con.execute("DESCRIBE gdelt").fetchall()

        print(f"Detected Columns : {len(cols)}")

        print([c[0] for c in cols])

        # --------------------------------------------------
        # Rename columns
        # --------------------------------------------------

        rename_sql = []

        for i, col in enumerate(GDELT_COLUMNS):

            rename_sql.append(
                f'column{i} AS "{col}"'
            )

        rename_sql = ",\n".join(rename_sql)

        con.execute(f"""
        CREATE OR REPLACE TABLE gdelt_events AS

        SELECT

        {rename_sql}

        FROM gdelt
        """)

        # --------------------------------------------------
        # India + Northeast Filter
        # --------------------------------------------------

        northeast = con.execute("""

        SELECT *

        FROM gdelt_events

        WHERE

        lower(ActionGeo_FullName) LIKE '%india%'

        OR lower(ActionGeo_FullName) LIKE '%assam%'

        OR lower(ActionGeo_FullName) LIKE '%arunachal%'

        OR lower(ActionGeo_FullName) LIKE '%manipur%'

        OR lower(ActionGeo_FullName) LIKE '%meghalaya%'

        OR lower(ActionGeo_FullName) LIKE '%mizoram%'

        OR lower(ActionGeo_FullName) LIKE '%nagaland%'

        OR lower(ActionGeo_FullName) LIKE '%tripura%'

        OR lower(ActionGeo_FullName) LIKE '%sikkim%'

        """).fetch_arrow_table()

        print(f"Filtered rows : {northeast.num_rows}")

        # --------------------------------------------------
        # Append to Parquet
        # --------------------------------------------------

        if northeast.num_rows > 0:

            df_new = northeast.to_pandas()

            if PARQUET_FILE.exists():

                df_old = pd.read_parquet(PARQUET_FILE)

                df_all = pd.concat(
                    [df_old, df_new],
                    ignore_index=True
                )

                if "GLOBALEVENTID" in df_all.columns:

                    df_all.drop_duplicates(
                        subset=["GLOBALEVENTID"],
                        inplace=True
                    )

            else:

                df_all = df_new

            df_all.to_parquet(
                PARQUET_FILE,
                index=False,
                engine="pyarrow"
            )

            print(f"Parquet Rows : {len(df_all):,}")

        processed += 1

    except Exception as e:

        failed += 1

        print("Stage 3/4 Error")
        print(e)

        continue

    finally:

        if "temp_csv" in locals():

            try:
                os.remove(temp_csv)
            except:
                pass


    # ======================================================
    # Update checkpoint
    # ======================================================

    checkpoint["last_index"] = idx

    with open(CHECKPOINT_FILE, "w") as f:

        json.dump(
            checkpoint,
            f,
            indent=4
        )

print()

print("=" * 70)
print("PIPELINE SUMMARY")
print("=" * 70)

print(f"Downloaded : {downloaded}")
print(f"Processed  : {processed}")
print(f"Skipped    : {skipped}")
print(f"Failed     : {failed}")
print()

print("Checkpoint")

print(checkpoint)

print()

print("Stage 1  ✓ Download Complete")
print("Stage 2  ✓ In-Memory Extraction Complete")
print("Stage 3  Waiting...")
print("Stage 4  ✓ Parquet Database Updated")
print("Stage 5  Waiting...")