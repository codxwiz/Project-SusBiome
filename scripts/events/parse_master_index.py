from pathlib import Path
import pandas as pd
import csv

# ==========================================================
# PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MASTER_FILE = (
    PROJECT_ROOT
    / "data/bronze/gdelt/index/masterfilelist.txt"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data/bronze/gdelt/index/event_file_index.csv"
)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# ==========================================================
# VERIFY
# ==========================================================

if not MASTER_FILE.exists():
    raise FileNotFoundError(MASTER_FILE)

print("=" * 60)
print("Parsing GDELT Master Index")
print("=" * 60)

print("Input :", MASTER_FILE)
print("Output:", OUTPUT_FILE)
print()

# ==========================================================
# PARSE
# ==========================================================

rows = 0
exports = 0

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as outfile:

    writer = csv.writer(outfile)

    writer.writerow([
        "timestamp",
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "size_bytes",
        "md5",
        "url",
        "filename"
    ])

    with open(
        MASTER_FILE,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as infile:

        for line in infile:

            rows += 1

            parts = line.strip().split()

            if len(parts) != 3:
                continue

            size_bytes, md5, url = parts

            # Only Event Export files
            if not url.endswith(".export.CSV.zip"):
                continue

            filename = url.split("/")[-1]

            timestamp = filename.split(".")[0]

            if len(timestamp) != 14:
                continue

            writer.writerow([
                timestamp,
                timestamp[:4],
                timestamp[4:6],
                timestamp[6:8],
                timestamp[8:10],
                timestamp[10:12],
                int(size_bytes),
                md5,
                url,
                filename
            ])

            exports += 1

            if exports % 100000 == 0:
                print(f"Processed {exports:,} export files...")

print()
print("=" * 60)
print("Completed")
print("=" * 60)

print(f"Total index rows      : {rows:,}")
print(f"Export files indexed  : {exports:,}")
print()

# ==========================================================
# QUICK VALIDATION
# ==========================================================

df = pd.read_csv(OUTPUT_FILE)

print(df.head())

print()

print("Years available:")

print(df["year"].value_counts().sort_index())

print()

print(f"Total export files: {len(df):,}")

print()

print("Saved to:")

print(OUTPUT_FILE)