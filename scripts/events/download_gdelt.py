from pathlib import Path
import requests
import zipfile
import io

# ==========================================================
# CONFIG
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data/bronze/gdelt/raw"
EXTRACT_DIR = PROJECT_ROOT / "data/bronze/gdelt/extracted"

RAW_DIR.mkdir(parents=True, exist_ok=True)
EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# SAMPLE FILES
# ==========================================================
#
# Start with a few known timestamps to validate the pipeline.
# Once this works we'll automate discovery from the master index.
#

FILES = [
    "20240101000000.export.CSV.zip",
    "20240101150000.export.CSV.zip",
    "20240102000000.export.CSV.zip",
]

BASE_URL = "http://data.gdeltproject.org/events"

# ==========================================================
# DOWNLOAD
# ==========================================================

downloaded = 0
failed = 0

for filename in FILES:

    url = f"{BASE_URL}/{filename}"

    print(f"\nDownloading {filename}")

    try:

        r = requests.get(url, timeout=120)

        if r.status_code != 200:

            print(f"HTTP {r.status_code}")

            failed += 1
            continue

        zip_path = RAW_DIR / filename

        with open(zip_path, "wb") as f:
            f.write(r.content)

        print("Downloaded")

        with zipfile.ZipFile(io.BytesIO(r.content)) as z:

            z.extractall(EXTRACT_DIR)

        print("Extracted")

        downloaded += 1

    except Exception as e:

        print(e)

        failed += 1

# ==========================================================
# SUMMARY
# ==========================================================

print("\n==============================")
print(f"Downloaded : {downloaded}")
print(f"Failed     : {failed}")
print("==============================")