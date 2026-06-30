from pathlib import Path
import pandas as pd

from gdeltdoc import GdeltDoc, Filters

# ==========================================================
# PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT = (
    PROJECT_ROOT /
    "data/bronze/events/gdelt_events.csv"
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# ==========================================================
# CONFIG
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
    ]
}

START_DATE = "2010-01-01"
END_DATE = "2025-12-31"

gd = GdeltDoc()

rows = []

# ==========================================================
# SEARCH
# ==========================================================

for state in STATES:

    print(f"\n========== {state} ==========")

    for event_type, keywords in EVENTS.items():

        for keyword in keywords:

            query = f'"{state}" AND "{keyword}"'

            print(query)

            try:

                filters = Filters(
                    keyword=query,
                    start_date=START_DATE,
                    end_date=END_DATE,
                )

                articles = gd.article_search(filters)

                if articles is None or len(articles) == 0:
                    continue

                print(f"Articles: {len(articles)}")

                for _, article in articles.iterrows():

                    rows.append({

                        "event_date":
                            article.get("seendate", ""),

                        "state":
                            state,

                        "event_type":
                            event_type,

                        "keyword":
                            keyword,

                        "headline":
                            article.get("title", ""),

                        "url":
                            article.get("url", ""),

                        "domain":
                            article.get("domain", ""),

                        "language":
                            article.get("language", ""),

                        "source":
                            "GDELT"

                    })

            except Exception as e:

                print(e)

# ==========================================================
# SAVE
# ==========================================================

df = pd.DataFrame(rows)

if not df.empty:

    df = df.drop_duplicates(subset=["url"])

    df = df.sort_values("event_date")

df.to_csv(
    OUTPUT,
    index=False
)

print("\n===================================")
print(f"Collected : {len(df)} articles")
print(f"Saved to  : {OUTPUT}")
print("===================================")