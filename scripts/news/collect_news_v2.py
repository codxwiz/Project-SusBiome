import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# ==========================================================
# PROJECT SETUP
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("NEWS_API_KEY")

if not API_KEY:
    raise ValueError("NEWS_API_KEY not found in .env")

# ==========================================================
# CONFIGURATION
# ==========================================================

STATES = [
    "Arunachal Pradesh",
    "Assam",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Sikkim",
    "Tripura",
]

EVENTS = {
    "flood": [
        "flood",
        "flash flood",
        "flooding",
    ],
    "drought": [
        "drought",
        "dry spell",
        "water shortage",
    ],
    "cyclone": [
        "cyclone",
        "cyclonic storm",
        "landfall",
    ],
}

URL = "https://newsapi.org/v2/everything"

HEADERS = {
    "X-Api-Key": API_KEY
}

OUTPUT_DIR = PROJECT_ROOT / "data" / "bronze" / "news"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "raw_news_articles.csv"

results = []

# ==========================================================
# COLLECT NEWS
# ==========================================================

for state in STATES:

    print(f"\n{'='*60}")
    print(f"STATE : {state}")

    for event_type, keywords in EVENTS.items():

        for keyword in keywords:

            query = f"{state} {keyword}"

            print(f"Searching: {query}")

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
                    timeout=30,
                )

                data = response.json()

                if data.get("status") != "ok":
                    print("ERROR:", data.get("message"))
                    continue

                articles = data.get("articles", [])

                print(f"Articles found: {len(articles)}")

                for article in articles:

                    results.append({

                        "date":
                            article.get("publishedAt", "")[:10],

                        "state_query":
                            state,

                        "event_type":
                            event_type,

                        "keyword":
                            keyword,

                        "headline":
                            article.get("title", ""),

                        "description":
                            article.get("description", ""),

                        "content":
                            article.get("content", ""),

                        "source":
                            article.get("source", {}).get("name", ""),

                        "author":
                            article.get("author", ""),

                        "url":
                            article.get("url", "")

                    })

            except Exception as e:

                print("ERROR:", e)

# ==========================================================
# SAVE
# ==========================================================

df = pd.DataFrame(results)

print("\nRemoving duplicate URLs...")

df = df.drop_duplicates(subset=["url"])

df = df.sort_values("date", ascending=False)

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n======================================")
print("Collection Complete")
print("Total Articles :", len(df))
print("Saved To:")
print(OUTPUT_FILE)
print("======================================")