from pathlib import Path
import pandas as pd
import requests
import time

# ==========================================================
# CONFIG
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

QUEUE = PROJECT_ROOT / "data/bronze/gdelt/index/download_queue.csv"

RAW = PROJECT_ROOT / "data/bronze/gdelt/raw"

LOG = PROJECT_ROOT / "data/bronze/gdelt/logs"

RAW.mkdir(parents=True, exist_ok=True)
LOG.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------
# CHANGE THIS NUMBER
# ----------------------------------------------------------

FILES_PER_RUN = 25

# ==========================================================
# LOAD QUEUE
# ==========================================================

queue = pd.read_csv(QUEUE)

downloaded = []

for _, row in queue.iterrows():

    filename = row.filename
    url = row.url

    target = RAW / filename

    if target.exists():
        continue

    downloaded.append((url, target))

    if len(downloaded) >= FILES_PER_RUN:
        break

print("=" * 60)
print(f"Files to download : {len(downloaded)}")
print("=" * 60)

success = 0
failed = 0

# ==========================================================
# DOWNLOAD
# ==========================================================

for url, target in downloaded:

    print(f"\nDownloading {target.name}")

    for attempt in range(3):

        try:

            r = requests.get(
                url,
                timeout=120,
                stream=True
            )

            r.raise_for_status()

            with open(target, "wb") as f:

                for chunk in r.iter_content(1024 * 1024):

                    if chunk:
                        f.write(chunk)

            success += 1

            print("✓ Success")

            break

        except Exception as e:

            print(f"Attempt {attempt+1}/3 failed")

            if attempt == 2:

                failed += 1

                with open(LOG / "download_failures.txt", "a") as log:

                    log.write(url + "\n")

            time.sleep(2)

print()

print("=" * 60)

print("DOWNLOAD COMPLETE")

print("=" * 60)

print(f"Success : {success}")

print(f"Failed  : {failed}")