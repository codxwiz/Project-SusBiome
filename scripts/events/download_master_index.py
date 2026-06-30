from pathlib import Path
import requests

# ==========================================================
# CONFIG
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "data" / "bronze" / "gdelt" / "index"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "masterfilelist.txt"

MASTER_INDEX_URL = "http://data.gdeltproject.org/gdeltv2/masterfilelist.txt"

# ==========================================================
# DOWNLOAD
# ==========================================================

print("=" * 60)
print("Downloading GDELT Master Index")
print("=" * 60)
print(f"Source : {MASTER_INDEX_URL}")
print(f"Output : {OUTPUT_FILE}")
print()

try:

    response = requests.get(
        MASTER_INDEX_URL,
        timeout=300,
        headers={
            "User-Agent": "SusBiome/1.0"
        }
    )

    response.raise_for_status()

    with open(OUTPUT_FILE, "wb") as f:
        f.write(response.content)

    print("Download successful.")

    file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)

    print(f"Saved: {OUTPUT_FILE.name}")
    print(f"Size : {file_size_mb:.2f} MB")

except requests.exceptions.HTTPError as e:

    print(f"HTTP Error : {e}")

except requests.exceptions.ConnectionError:

    print("Connection failed.")

except requests.exceptions.Timeout:

    print("Connection timed out.")

except Exception as e:

    print(f"Unexpected error : {e}")

# ==========================================================
# VERIFY
# ==========================================================

if OUTPUT_FILE.exists():

    print("\nPreview:\n")

    with open(OUTPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:

        for i in range(10):

            line = f.readline()

            if not line:
                break

            print(line.rstrip())

print("\nDone.")