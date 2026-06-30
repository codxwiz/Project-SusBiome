import pandas as pd
from pathlib import Path

# ==========================================================
# PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data/bronze/news/raw_news_articles.csv"
OUTPUT_FILE = PROJECT_ROOT / "data/silver/news/verified_events.csv"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# ==========================================================
# LOAD DATA
# ==========================================================

print("Loading raw news...")

df = pd.read_csv(INPUT_FILE)

print(f"Loaded {len(df)} articles")

# ==========================================================
# PASS 1
# STRUCTURAL CLEANING
# ==========================================================

print("\nPASS 1 : Structural Cleaning")

# Fill missing values
for col in [
    "headline",
    "description",
    "content",
    "source",
    "url",
]:
    df[col] = df[col].fillna("").astype(str).str.strip()

# Remove empty headlines
before = len(df)

df = df[df["headline"] != ""]

print(f"Removed empty headlines : {before-len(df)}")

# Remove empty URLs
before = len(df)

df = df[df["url"] != ""]

print(f"Removed empty URLs      : {before-len(df)}")

# Remove duplicate URLs
before = len(df)

df = df.drop_duplicates(subset=["url"])

print(f"Removed duplicate URLs  : {before-len(df)}")

# Remove duplicate headlines
before = len(df)

df = df.drop_duplicates(subset=["headline"])

print(f"Removed duplicate titles: {before-len(df)}")

# ==========================================================
# NORMALIZE
# ==========================================================

df["headline_lower"] = df["headline"].str.lower()
df["description_lower"] = df["description"].str.lower()
df["content_lower"] = df["content"].str.lower()

# ==========================================================
# PASS 2
# CONTENT VALIDATION
# ==========================================================

print("\nPASS 2 : Content Validation")

FORECAST_WORDS = [
    "weather tomorrow",
    "weather update",
    "forecast",
    "imd forecast",
    "rain alert",
    "weather warning",
    "expected rainfall",
    "heavy rainfall expected",
]

BAD_TOPICS = [
    "vacation",
    "tourism",
    "travel",
    "wildlife",
    "celebrity",
    "movie",
    "exam",
    "neet",
    "job",
    "vacancy",
    "gemini",
    "show hn",
]

EVENT_WORDS = {

    "flood": [
        "flood",
        "flash flood",
        "flooding",
        "overflow",
        "embankment",
        "river",
        "inundation",
    ],

    "drought": [
        "drought",
        "dry spell",
        "water shortage",
        "water crisis",
    ],

    "cyclone": [
        "cyclone",
        "cyclonic storm",
        "landfall",
        "storm surge",
        "deep depression",
    ],
}

# ----------------------------------------------------------
# CLEANING FUNCTION
# ----------------------------------------------------------

def is_valid(row):

    text = " ".join([
        row["headline_lower"],
        row["description_lower"],
        row["content_lower"],
    ])

    # ------------------------------------------------------
    # Must mention queried state
    # ------------------------------------------------------

    state = row["state_query"].lower()

    state_tokens = [w for w in state.split() if len(w) > 2]

    if not any(token in text for token in state_tokens):
        return False

    # ------------------------------------------------------
    # Remove weather forecasts
    # ------------------------------------------------------

    if any(word in text for word in FORECAST_WORDS):
        return False

    # ------------------------------------------------------
    # Remove irrelevant topics
    # ------------------------------------------------------

    if any(word in text for word in BAD_TOPICS):
        return False

    # ------------------------------------------------------
    # Must contain disaster keywords
    # ------------------------------------------------------

    keywords = EVENT_WORDS.get(
        row["event_type"],
        []
    )

    if not any(word in text for word in keywords):
        return False

    return True

# ----------------------------------------------------------
# APPLY FILTER
# ----------------------------------------------------------

before = len(df)

df = df[df.apply(is_valid, axis=1)]

print(f"Removed noisy articles  : {before-len(df)}")

# ==========================================================
# DROP HELPER COLUMNS
# ==========================================================

df = df.drop(
    columns=[
        "headline_lower",
        "description_lower",
        "content_lower",
    ]
)

# ==========================================================
# SORT
# ==========================================================

df = df.sort_values(
    "date",
    ascending=False,
)

# ==========================================================
# SAVE
# ==========================================================

df.to_csv(
    OUTPUT_FILE,
    index=False,
)

print("\n===================================")
print(f"Verified events : {len(df)}")
print(f"Saved to:")
print(OUTPUT_FILE)
print("===================================")