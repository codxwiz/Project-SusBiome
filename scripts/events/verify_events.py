import pandas as pd
from pathlib import Path

# ==========================================================
# PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data/silver/news/verified_events.csv"

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data/silver/events/verified_events_final.csv"
)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# ==========================================================
# LOAD
# ==========================================================

print("Loading verified events...")

df = pd.read_csv(INPUT_FILE)

print(f"Articles loaded : {len(df)}")

# ==========================================================
# KEYWORDS
# ==========================================================

KEEP_WORDS = [

    # Disaster impact
    "flood",
    "flash flood",
    "flooding",
    "cyclone",
    "cyclonic storm",
    "landfall",
    "storm surge",
    "drought",
    "water shortage",
    "dry spell",

    # Damage
    "death",
    "dead",
    "missing",
    "damage",
    "destroyed",
    "washed away",
    "collapsed",
    "marooned",
    "evacuated",
    "rescue",
    "relief",
    "displaced",

    # Preparedness
    "preparedness",
    "embankment",
    "ndrf",
    "sdrf",
    "disaster management",
    "warning",
]

DROP_WORDS = [

    "hydropower",
    "power project",
    "renewable energy",
    "agreement",
    "memorandum",

    "drone",
    "air mobility",

    "tourism",
    "vacation",
    "travel",

    "movie",
    "celebrity",
    "exam",
    "neet",

    "share market",
    "stock market",

    "startup",

    "gemini",

    "show hn",
]

# ==========================================================
# VERIFY
# ==========================================================

verified = []

removed = 0

for _, row in df.iterrows():

    text = " ".join([

        str(row.get("headline", "")),
        str(row.get("description", "")),
        str(row.get("content", ""))

    ]).lower()

    keep_score = 0
    drop_score = 0

    for word in KEEP_WORDS:

        if word in text:
            keep_score += 1

    for word in DROP_WORDS:

        if word in text:
            drop_score += 1

    # Keep only genuine disaster articles
    if keep_score > drop_score:

        row["verification_score"] = keep_score - drop_score

        verified.append(row)

    else:

        removed += 1

# ==========================================================
# SAVE
# ==========================================================

verified_df = pd.DataFrame(verified)

verified_df = verified_df.sort_values(
    "date",
    ascending=False
)

verified_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print()

print("=" * 50)
print(f"Input Articles      : {len(df)}")
print(f"Verified Articles   : {len(verified_df)}")
print(f"Removed             : {removed}")
print("=" * 50)

print(f"\nSaved to:\n{OUTPUT_FILE}")