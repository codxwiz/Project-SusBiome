import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# ==========================================================
# LOAD ENVIRONMENT
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("NEWS_API_KEY")

if not API_KEY:
    raise RuntimeError("NEWS_API_KEY not found in .env")

API_KEY = API_KEY.strip()

print("=" * 60)
print("Project Root :", PROJECT_ROOT)
print("API Loaded   :", True)
print("Key Length   :", len(API_KEY))
print("=" * 60)

# ==========================================================
# LOAD LOCATIONS
# ==========================================================

locations = pd.read_csv(
    PROJECT_ROOT / "data/raw/locations.csv"
)

# ----------------------------------------------------------
# TEST MODE
# Uncomment the next line while testing
# ----------------------------------------------------------

locations = (
    locations[locations["state"] == "Assam"]
    .head(5)
)

# ==========================================================
# SEARCH QUERIES
# ==========================================================

EVENT_QUERIES = {
    "flood": [
        "flood",
        "flash flood",
        "flooding",
        "river overflow",
        "embankment breach",
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
    ],
}

# ==========================================================
# NEWS API
# ==========================================================

URL = "https://newsapi.org/v2/everything"

HEADERS = {
    "X-Api-Key": API_KEY
}

results = []
seen = set()

# ==========================================================
# COLLECT NEWS
# ==========================================================

for _, row in locations.iterrows():

    state = row["state"]
    district = row["district"]

    print(f"\nChecking {district}, {state}")

    for event_type, keywords in EVENT_QUERIES.items():

        for keyword in keywords:

            query = f"{state} {keyword}"

            params = {
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 100,
            }

            try:

                response = requests.get(
                    URL,
                    headers=HEADERS,
                    params=params,
                    timeout=20,
                )

                data = response.json()

                print(
                    f"{event_type.upper():9} | "
                    f"{keyword:20} | "
                    f"{len(data.get('articles', []))} articles"
                )

                if data.get("status") != "ok":
                    print(data)
                    continue

                for article in data.get("articles", []):

                    article_url = article.get("url", "")

                    if article_url in seen:
                        continue

                    seen.add(article_url)

                    results.append({

                        "date":
                            article.get(
                                "publishedAt",
                                ""
                            )[:10],

                        "state":
                            state,

                        "district":
                            district,

                        "event_type":
                            event_type,

                        "headline":
                            article.get(
                                "title",
                                ""
                            ),

                        "description":
                            article.get(
                                "description",
                                ""
                            ),

                        "content":
                            article.get(
                                "content",
                                ""
                            ),

                        "source":
                            article.get(
                                "source",
                                {}
                            ).get(
                                "name",
                                ""
                            ),

                        "author":
                            article.get(
                                "author",
                                ""
                            ),

                        "url":
                            article_url,
                    })

            except Exception as e:

                print("ERROR:", e)

# ==========================================================
# SAVE
# ==========================================================

df = pd.DataFrame(results)

df = df.sort_values(
    "date",
    ascending=False,
)

output_dir = PROJECT_ROOT / "data/labels"
output_dir.mkdir(
    parents=True,
    exist_ok=True,
)

output_file = output_dir / "disaster_news.csv"

df.to_csv(
    output_file,
    index=False,
)

print()
print("=" * 60)
print("Collection Complete")
print("Total Articles :", len(df))
print("Saved To       :", output_file)
print("=" * 60)