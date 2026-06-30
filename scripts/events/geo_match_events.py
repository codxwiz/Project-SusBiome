import pandas as pd
from pathlib import Path

# ==========================================================
# PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

EVENTS_FILE = PROJECT_ROOT / "data/silver/events/verified_events_final.csv"
LOCATIONS_FILE = PROJECT_ROOT / "data/raw/locations.csv"

OUTPUT_FILE = PROJECT_ROOT / "data/gold/events/district_events.csv"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# ==========================================================
# LOAD DATA
# ==========================================================

print("Loading verified events...")

events = pd.read_csv(EVENTS_FILE)

print(f"Events loaded : {len(events)}")

print("Loading locations...")

locations = pd.read_csv(LOCATIONS_FILE)

print(f"Districts loaded : {len(locations)}")

# ==========================================================
# MATCH DISTRICTS
# ==========================================================

matched_events = []

for _, event in events.iterrows():

    state = str(event["state_query"]).strip()

    headline = str(event.get("headline", ""))
    description = str(event.get("description", ""))
    content = str(event.get("content", ""))

    text = f"{headline} {description} {content}".lower()

    state_districts = locations[
        locations["state"].str.lower() == state.lower()
    ]

    found = False

    for _, district_row in state_districts.iterrows():

        district = str(district_row["district"]).strip()

        if district.lower() in text:

            matched_events.append({

                "date": event["date"],
                "state": state,
                "district": district,
                "event_type": event["event_type"],
                "headline": event["headline"],
                "source": event["source"],
                "url": event["url"],
                "match_method": "district_name"

            })

            found = True

    if not found:

        matched_events.append({

            "date": event["date"],
            "state": state,
            "district": "UNKNOWN",
            "event_type": event["event_type"],
            "headline": event["headline"],
            "source": event["source"],
            "url": event["url"],
            "match_method": "none"

        })

# ==========================================================
# SAVE
# ==========================================================

district_df = pd.DataFrame(matched_events)

district_df = district_df.drop_duplicates()

district_df = district_df.sort_values(
    ["date", "state", "district"],
    ascending=[False, True, True]
)

district_df.to_csv(
    OUTPUT_FILE,
    index=False
)

# ==========================================================
# SUMMARY
# ==========================================================

matched = district_df[district_df["district"] != "UNKNOWN"]

unknown = district_df[district_df["district"] == "UNKNOWN"]

print("\n===================================")
print(f"Verified events : {len(events)}")
print(f"District matches: {len(matched)}")
print(f"Unknown matches : {len(unknown)}")
print("===================================")

print("\nSaved to:")
print(OUTPUT_FILE)