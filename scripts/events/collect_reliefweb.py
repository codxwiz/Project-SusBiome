import requests
import pandas as pd
from pathlib import Path

# ==========================================================
# PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT = (
    PROJECT_ROOT /
    "data/bronze/events/reliefweb_events.csv"
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# ==========================================================
# API
# ==========================================================

URL = "https://api.reliefweb.int/v1/reports"

PARAMS = {
    "appname": "SusBiome",
    "limit": 100,
    "profile": "full"
}

print("Downloading ReliefWeb reports...")

response = requests.get(URL, params=PARAMS, timeout=60)

response.raise_for_status()

data = response.json()

rows = []

for item in data.get("data", []):

    fields = item.get("fields", {})

    title = fields.get("title", "")

    body = fields.get("body", "")

    source = ""

    if fields.get("source"):
        source = fields["source"][0].get("shortname", "")

    date = ""

    if fields.get("date"):
        date = fields["date"].get("created", "")[:10]

    url = fields.get("origin", "")

    rows.append({

        "event_date": date,
        "headline": title,
        "description": body,
        "source": source,
        "source_type": "ReliefWeb",
        "url": url

    })

df = pd.DataFrame(rows)

df.to_csv(
    OUTPUT,
    index=False
)

print(f"Saved {len(df)} reports")

print(OUTPUT)