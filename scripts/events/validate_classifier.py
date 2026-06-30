from pathlib import Path
import pandas as pd

# ==========================================================
# PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GDELT_FILE = PROJECT_ROOT / "data/bronze/gdelt/parsed_events.csv"

GROUND_TRUTH = PROJECT_ROOT / "data/gold/events/district_events.csv"

OUTPUT_DIR = PROJECT_ROOT / "data/gold/validation"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MATCHES_FILE = OUTPUT_DIR / "matches.csv"
MISSED_FILE = OUTPUT_DIR / "missed_events.csv"
FALSE_POS_FILE = OUTPUT_DIR / "false_positives.csv"

# ==========================================================
# LOAD DATA
# ==========================================================

print("Loading datasets...")

gdelt = pd.read_csv(GDELT_FILE, low_memory=False)

truth = pd.read_csv(GROUND_TRUTH)

print(f"GDELT events : {len(gdelt):,}")
print(f"Ground truth : {len(truth):,}")

# ==========================================================
# STANDARDIZE
# ==========================================================

for df in (gdelt, truth):

    df.columns = df.columns.str.lower()

required_truth = [
    "date",
    "state",
    "district",
    "event_type"
]

required_gdelt = [
    "sqldate",
    "actiongeo_fullname",
    "eventrootcode"
]

for c in required_truth:

    if c not in truth.columns:
        raise ValueError(f"Missing column in ground truth: {c}")

for c in required_gdelt:

    if c not in gdelt.columns:
        raise ValueError(f"Missing column in GDELT: {c}")

truth["date"] = pd.to_datetime(truth["date"])

gdelt["date"] = pd.to_datetime(
    gdelt["sqldate"],
    format="%Y%m%d",
    errors="coerce"
)

gdelt["location"] = (
    gdelt["actiongeo_fullname"]
    .fillna("")
    .str.lower()
)

# ==========================================================
# MATCHING
# ==========================================================

matches = []
missed = []

for _, event in truth.iterrows():

    state = str(event["state"]).lower()

    district = str(event["district"]).lower()

    start = event["date"] - pd.Timedelta(days=2)
    end = event["date"] + pd.Timedelta(days=2)

    candidate = gdelt[
        (gdelt["date"] >= start) &
        (gdelt["date"] <= end)
    ]

    location_match = candidate[
        candidate["location"].str.contains(
            district,
            na=False
        )
    ]

    if location_match.empty:

        location_match = candidate[
            candidate["location"].str.contains(
                state,
                na=False
            )
        ]

    if location_match.empty:

        missed.append(event)

    else:

        first = location_match.iloc[0]

        row = event.to_dict()

        row["gdelt_date"] = first["date"]

        row["gdelt_location"] = first["actiongeo_fullname"]

        row["gdelt_eventroot"] = first["eventrootcode"]

        row["gdelt_url"] = first.get(
            "sourceurl",
            ""
        )

        matches.append(row)

# ==========================================================
# FALSE POSITIVES
# ==========================================================

matched_locations = {
    str(x["gdelt_location"]).lower()
    for x in matches
}

false_positive = gdelt[
    ~gdelt["location"].isin(
        matched_locations
    )
]

# ==========================================================
# SAVE
# ==========================================================

matches_df = pd.DataFrame(matches)

missed_df = pd.DataFrame(missed)

matches_df.to_csv(
    MATCHES_FILE,
    index=False
)

missed_df.to_csv(
    MISSED_FILE,
    index=False
)

false_positive.to_csv(
    FALSE_POS_FILE,
    index=False
)

# ==========================================================
# METRICS
# ==========================================================

tp = len(matches_df)

fn = len(missed_df)

fp = len(false_positive)

precision = tp / (tp + fp) if tp + fp else 0

recall = tp / (tp + fn) if tp + fn else 0

f1 = (
    2 * precision * recall /
    (precision + recall)
    if precision + recall else 0
)

# ==========================================================
# REPORT
# ==========================================================

print("\n==============================")
print("VALIDATION REPORT")
print("==============================")

print(f"Ground Truth      : {len(truth):,}")
print(f"Matches           : {tp:,}")
print(f"Missed            : {fn:,}")
print(f"False Positives   : {fp:,}")

print()

print(f"Precision : {precision:.3f}")
print(f"Recall    : {recall:.3f}")
print(f"F1 Score  : {f1:.3f}")

print("\nSaved:")

print(MATCHES_FILE)

print(MISSED_FILE)

print(FALSE_POS_FILE)