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
    raise RuntimeError(
        "NEWS_API_KEY not found in .env"
    )

API_KEY = API_KEY.strip()

print("Working Directory :", os.getcwd())
print("Project Root      :", PROJECT_ROOT)
print("API Loaded        :", True)
print("API Key Length    :", len(API_KEY))

# ==========================================================
# LOAD DISTRICTS
# ==========================================================

locations = pd.read_csv(
    PROJECT_ROOT / "data/raw/locations.csv"
)

# Test only first 5 Assam districts
locations = (
    locations[locations["state"] == "Assam"]
    .head(5)
)

# ==========================================================
# SEARCH TERMS
# ==========================================================

EVENT_QUERIES = {
    "flood": [
        "flood",
        "flooding",
        "heavy rainfall",
    ],
    "drought": [
        "drought",
        "dry spell",
        "water shortage",
    ],
    "cyclone": [
        "cyclone",
        "cyclonic storm",
        "severe cyclonic storm",
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

                print("\nRequest URL:")
                print(response.url)

                print("HTTP Status:", response.status_code)

                data = response.json()

                print("Status :", data.get("status"))
                print("Code   :", data.get("code"))
                print("Message:", data.get("message"))

                if data.get("status") != "ok":
                    continue

                articles = data.get("articles", [])

                print(f"Articles Found: {len(articles)}")

                for article in articles:

                    article_id = (
                        article.get("publishedAt"),
                        article.get("title"),
                    )

                    if article_id in seen:
                        continue

                    seen.add(article_id)

                    results.append({
                        "date": article.get("publishedAt", "")[:10],
                        "state": state,
                        "district": district,
                        "event_type": event_type,
                        "headline": article.get("title"),
                        "source": article.get("source", {}).get("name"),
                        "url": article.get("url"),
                    })

            except Exception as e:

                print("ERROR:", e)

# ==========================================================
# SAVE
# ==========================================================

output_dir = PROJECT_ROOT / "data/labels"
output_dir.mkdir(parents=True, exist_ok=True)

df = pd.DataFrame(results)

print("\n==============================")
print("TOTAL ARTICLES:", len(df))
print("==============================")

output_file = output_dir / "disaster_news.csv"

df.to_csv(
    output_file,
    index=False,
)

print(f"\nSaved to:\n{output_file}")