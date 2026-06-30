from pathlib import Path
import pandas as pd

# ==========================================================
# CONFIG
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INDEX_FILE = (
    PROJECT_ROOT /
    "data/bronze/gdelt/index/event_file_index.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT /
    "data/bronze/gdelt/index/download_queue.csv"
)

# ----------------------------------------------------------
# DOWNLOAD RANGE
# ----------------------------------------------------------

START_YEAR = 2015
END_YEAR = 2025

# Northeast India disaster season
MONTHS = [5, 6, 7, 8, 9, 10]

# ==========================================================
# LOAD
# ==========================================================

print("=" * 60)
print("Building Download Queue")
print("=" * 60)

print("Loading index...")

df = pd.read_csv(
    INDEX_FILE,
    usecols=[
        "timestamp",
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "url",
        "filename",
        "size_bytes"
    ]
)

print(f"Loaded {len(df):,} export files")

# ==========================================================
# CLEAN TYPES
# ==========================================================

df["year"] = df["year"].astype(int)
df["month"] = df["month"].astype(int)

# ==========================================================
# FILTER YEAR
# ==========================================================

queue = df[
    (df["year"] >= START_YEAR) &
    (df["year"] <= END_YEAR)
]

print(f"After year filter : {len(queue):,}")

# ==========================================================
# FILTER MONTH
# ==========================================================

queue = queue[
    queue["month"].isin(MONTHS)
]

print(f"After month filter: {len(queue):,}")

# ==========================================================
# SORT
# ==========================================================

queue = queue.sort_values(
    ["year", "month", "day", "hour", "minute"]
)

# ==========================================================
# ESTIMATE DOWNLOAD SIZE
# ==========================================================

total_bytes = queue["size_bytes"].sum()

total_mb = total_bytes / 1024 / 1024
total_gb = total_mb / 1024

# ==========================================================
# SAVE
# ==========================================================

queue.to_csv(
    OUTPUT_FILE,
    index=False
)

# ==========================================================
# SUMMARY
# ==========================================================

print()

print("=" * 60)
print("Download Queue Ready")
print("=" * 60)

print(f"Files selected : {len(queue):,}")
print(f"Estimated size : {total_gb:.2f} GB")

print()

print("Years:")

print(queue["year"].value_counts().sort_index())

print()

print("Months:")

print(queue["month"].value_counts().sort_index())

print()

print("Saved:")

print(OUTPUT_FILE)