from pathlib import Path
import requests
import zipfile
import shutil
import pandas as pd
import io
import os
print("=" * 60)
print("download_and_filter.py STARTED")
print("=" * 60)

# ==========================================================
# CONFIG
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

QUEUE_FILE = PROJECT_ROOT / "data/bronze/gdelt/index/download_queue.csv"

RAW_DIR = PROJECT_ROOT / "data/bronze/gdelt/raw"
EXTRACT_DIR = PROJECT_ROOT / "data/bronze/gdelt/extracted"
INDIA_DIR = PROJECT_ROOT / "data/bronze/gdelt/india"

RAW_DIR.mkdir(parents=True, exist_ok=True)
EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
INDIA_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------
# TEST MODE
# ----------------------------------------------------------
#
# IMPORTANT
#
# Start with ONE file.
#
# Change later to:
#
# FILE_LIMIT = None
#
# for full pipeline
#

FILE_LIMIT = 1

# ==========================================================
# LOAD QUEUE
# ==========================================================

queue = pd.read_csv(QUEUE_FILE)

if FILE_LIMIT is not None:
    queue = queue.head(FILE_LIMIT)

print("=" * 60)
print(f"Files to process : {len(queue)}")
print("=" * 60)

# ==========================================================
# PROCESS
# ==========================================================

for _, row in queue.iterrows():

    filename = row["filename"]
    url = row["url"]

    print("\n--------------------------------------------")
    print(filename)

    zip_path = RAW_DIR / filename

    csv_name = filename.replace(".zip", "")

    csv_path = EXTRACT_DIR / csv_name

    output_path = INDIA_DIR / csv_name

    # ------------------------------------------------------
    # DOWNLOAD
    # ------------------------------------------------------

    try:

        r = requests.get(url, timeout=180)

        r.raise_for_status()

        with open(zip_path, "wb") as f:
            f.write(r.content)

        print("Downloaded")

    except Exception as e:

        print(e)
        continue

    # ------------------------------------------------------
    # EXTRACT
    # ------------------------------------------------------

    try:

        with zipfile.ZipFile(zip_path, "r") as z:

            z.extractall(EXTRACT_DIR)

        print("Extracted")

    except Exception as e:

        print(e)
        continue

    # ------------------------------------------------------
    # LOAD CSV
    # ------------------------------------------------------

    try:

        df = pd.read_csv(
            csv_path,
            sep="\t",
            header=None,
            low_memory=False
        )

        print(f"Rows : {len(df):,}")

    except Exception as e:

        print(e)
        continue

    # ------------------------------------------------------
    # SAVE TEMP
    # ------------------------------------------------------

    df.to_csv(
        output_path,
        index=False
    )

    print("Saved")

    # ------------------------------------------------------
    # CLEANUP
    # ------------------------------------------------------

    try:

        os.remove(zip_path)
    except:
        pass

    try:
        os.remove(csv_path)
    except:
        pass

print("\n======================================")
print("Pipeline Complete")
print("======================================")