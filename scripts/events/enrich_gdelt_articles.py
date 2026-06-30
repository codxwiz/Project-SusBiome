"""
============================================================
SusBiome GDELT Article Enrichment Pipeline
============================================================

Reads:

    data/silver/events/gdelt_candidate_events.parquet

Downloads article webpages from SOURCEURL.

Extracts:

    • headline
    • article text
    • disaster keywords
    • location mentions
    • article quality
    • enrichment confidence

Writes:

    data/silver/events/gdelt_enriched_candidates.parquet

Author:
    SusBiome
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time

from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from numpy.strings import title
import pandas as pd
import requests

from bs4 import BeautifulSoup  # type: ignore[reportMissingImports]

from requests.adapters import HTTPAdapter

from urllib3.util.retry import Retry
# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PARQUET = (
    PROJECT_ROOT
    / "data/silver/events/gdelt_candidate_events.parquet"
)

OUTPUT_PARQUET = (
    PROJECT_ROOT
    / "data/silver/events/gdelt_enriched_candidates.parquet"
)

OUTPUT_CSV = (
    PROJECT_ROOT
    / "data/silver/events/gdelt_enriched_candidates.csv"
)

SUMMARY_JSON = (
    PROJECT_ROOT
    / "data/bronze/gdelt/logs/enrich_gdelt_articles_summary.json"
)

LOG_FILE = (
    PROJECT_ROOT
    / "data/bronze/gdelt/logs/enrich_gdelt_articles.log"
)
# ==========================================================
# HTTP
# ==========================================================

USER_AGENT = (

    "SusBiome/1.0 "
    "(Research Pipeline)"

)

REQUEST_TIMEOUT = 20

MAX_RETRIES = 3

SLEEP_SECONDS = 1
# ==========================================================
# OUTPUT SCHEMA
# ==========================================================

OUTPUT_COLUMNS = [

    "candidate_id",

    "gdelt_event_id",

    "event_date",

    "country",

    "state",

    "district",

    "event_type",

    "candidate_score",

    "headline",

    "article_title",

    "article_description",

    "article_text",

    "article_length",

    "disaster_keywords",

    "matched_keyword",

    "hazard_type",

    "location_mentions",

    "article_quality",

    "enrichment_confidence",

    "article_score",

    "disaster_score",

    "location_score",

    "relevance_score",

    "source_url",

    "retrieved",

    "http_status",

    "retrieved_at",

]
# ==========================================================
# LOGGING
# ==========================================================

logger = logging.getLogger("gdelt_enrichment")

logger.setLevel(logging.INFO)

formatter = logging.Formatter(

    "%(asctime)s | %(levelname)s | %(message)s"

)

console = logging.StreamHandler()

console.setFormatter(formatter)

logger.addHandler(console)
# ==========================================================
# CLI
# ==========================================================

def parse_args():

    parser = argparse.ArgumentParser(

        description="Enrich GDELT candidate events using article webpages."

    )

    parser.add_argument(

        "--csv",

        action="store_true",

        help="Also export CSV."

    )

    parser.add_argument(

        "--limit",

        type=int,

        default=None,

        help="Limit number of rows."

    )

    parser.add_argument(

        "--resume",

        action="store_true",

        help="Skip already enriched rows."

    )

    return parser.parse_args()
# ==========================================================
# HTTP SESSION
# ==========================================================

def build_session():

    retry = Retry(

        total=MAX_RETRIES,

        connect=MAX_RETRIES,

        read=MAX_RETRIES,

        backoff_factor=1,

        status_forcelist=[

            429,

            500,

            502,

            503,

            504

        ]

    )

    adapter = HTTPAdapter(

        max_retries=retry

    )

    session = requests.Session()

    session.headers.update(

        {

            "User-Agent": USER_AGENT

        }

    )

    session.mount(

        "http://",

        adapter

    )

    session.mount(

        "https://",

        adapter

    )

    return session
# ==========================================================
# LOAD DATASET
# ==========================================================

def load_dataset():

    logger.info(

        "Loading candidate events."

    )

    df = pd.read_parquet(

        INPUT_PARQUET

    )

    logger.info(

        f"Loaded {len(df):,} candidates."

    )

    return df
# ==========================================================
# DOWNLOAD HTML
# ==========================================================

def download_html(

    session,

    url

):

    if pd.isna(url):

        return None, None

    try:

        response = session.get(

            url,

            timeout=REQUEST_TIMEOUT

        )

        return (

            response.status_code,

            response.text

        )

    except Exception:

        return (

            None,

            None

        )
    # ==========================================================
# HTML CLEANUP
# ==========================================================

def clean_html(html):

    if not html:

        return ""

    soup = BeautifulSoup(

        html,

        "html.parser"

    )

    for tag in soup(

        [

            "script",

            "style",

            "noscript",

            "svg",

            "footer",

            "header",

            "nav"

        ]

    ):

        tag.decompose()

    text = soup.get_text(

        separator=" "

    )

    text = re.sub(

        r"\s+",

        " ",

        text

    )

    return text.strip()
# ==========================================================
# HEADLINE EXTRACTION
# ==========================================================

def extract_headline(soup):

    if soup.title and soup.title.text.strip():

        return soup.title.text.strip()

    for tag in [

        "h1",

        "h2"

    ]:

        node = soup.find(tag)

        if node:

            text = node.get_text(

                " ",

                strip=True

            )

            if text:

                return text

    return None


# ==========================================================
# META DESCRIPTION
# ==========================================================

def extract_description(soup):

    tags = [

        {

            "name": "description"

        },

        {

            "property": "og:description"

        },

        {

            "name": "twitter:description"

        }

    ]

    for attrs in tags:

        meta = soup.find(

            "meta",

            attrs=attrs

        )

        if meta:

            value = meta.get(

                "content"

            )

            if value:

                return value.strip()

    return None
# ==========================================================
# ARTICLE BODY
# ==========================================================

def extract_article_text(soup):

    blocks = []

    article = soup.find("article")

    if article:

        blocks = article.find_all("p")

    if not blocks:

        blocks = soup.find_all("p")

    text = []

    for block in blocks:

        value = block.get_text(

            " ",

            strip=True

        )

        if len(value) >= 30:

            text.append(value)

    article_text = "\n\n".join(text)

    article_text = re.sub(

        r"\n{3,}",

        "\n\n",

        article_text

    )

    return article_text.strip()
# ==========================================================
# DISASTER KEYWORDS
# ==========================================================

DISASTER_KEYWORDS = {

    "FLOOD":[

        "flood",

        "flooding",

        "flash flood",

        "river overflow",

        "waterlogging",

        "embankment",

        "inundation"

    ],

    "DROUGHT":[

        "drought",

        "dry spell",

        "rainfall deficit",

        "water shortage"

    ],

    "CYCLONE":[

        "cyclone",

        "cyclonic storm",

        "storm surge",

        "landfall"

    ],

    "LANDSLIDE":[

        "landslide",

        "mudslide",

        "rockfall"

    ]

}

HAZARD_PRIORITY = list(DISASTER_KEYWORDS.keys())


def analyze_disaster_keywords(text):

    if not text:

        return [], None, None

    lower = text.lower()

    found = []

    hazard_scores = {}

    matched_keyword = None

    for hazard in HAZARD_PRIORITY:

        score = 0

        for keyword in DISASTER_KEYWORDS[hazard]:

            if keyword in lower:

                found.append(keyword)

                score += 1

                if matched_keyword is None:

                    matched_keyword = keyword

        hazard_scores[hazard] = score

    found = sorted(set(found))

    hazard_type = None

    if hazard_scores:

        best = max(

            hazard_scores,

            key=hazard_scores.get

        )

        if hazard_scores[best] > 0:

            hazard_type = best

    return (

        found,

        matched_keyword,

        hazard_type

    )
# ==========================================================
# LOCATION EXTRACTION
# ==========================================================

LOCATION_WORDS = [

    "assam",

    "arunachal pradesh",

    "manipur",

    "mizoram",

    "nagaland",

    "meghalaya",

    "tripura",

    "sikkim"

]


def extract_locations(text):

    lower = text.lower()

    locations = []

    for location in LOCATION_WORDS:

        if location in lower:

            locations.append(location.title())

    return sorted(

        set(locations)

    )
# ==========================================================
# ARTICLE QUALITY
# ==========================================================

def article_quality(

    article_text,

    keywords

):

    score = 0

    length = len(article_text)

    if length > 500:

        score += 40

    elif length > 200:

        score += 25

    elif length > 100:

        score += 15

    score += min(

        len(keywords) * 10,

        40

    )

    return min(

        score,

        100

    )
# ==========================================================
# ENRICHMENT CONFIDENCE
# ==========================================================

def enrichment_confidence(

    headline,

    article,

    keywords,

    locations

):

    score = 0

    if headline:

        score += 20

    if article:

        score += 30

    score += min(

        len(keywords) * 10,

        30

    )

    score += min(

        len(locations) * 10,

        20

    )

    return min(

        score,

        100

    )

# ==========================================================
# ARTICLE INTELLIGENCE
# ==========================================================

def analyze_article(

    title,

    article,

    disaster_keywords,

    locations,

):

    disaster_score = min(

        len(disaster_keywords) * 20,

        100

    )

    location_score = min(

        len(locations) * 15,

        100

    )

    relevance_score = 0

    lower = article.lower()

    if title:

        relevance_score += 10

    if len(article) > 300:

        relevance_score += 20

    if disaster_keywords:

        relevance_score += 30

    if locations:

        relevance_score += 20

    if any(

        word in lower

        for word in (

            "killed",

            "dead",

            "missing",

            "evacuated",

            "damage",

            "destroyed",

            "rescue",

            "relief",

        )

    ):

        relevance_score += 20

    relevance_score = min(

        relevance_score,

        100

    )

    article_score = int(

        (

            disaster_score * 0.45

            +

            location_score * 0.20

            +

            relevance_score * 0.35

        )

    )

    return {

        "disaster_score":

            disaster_score,

        "location_score":

            location_score,

        "relevance_score":

            relevance_score,

        "article_score":

            article_score,

    }
# ==========================================================
# BUILD ENRICHED RECORD
# ==========================================================

def build_enriched_record(

    row,

    session

):

    status, html = download_html(

        session,

        row["source_url"]

    )

    if html is None:

        return {

            **row.to_dict(),

            "article_title": None,

            "article_description": None,

            "article_text": None,

            "article_length": 0,

            "disaster_keywords": [],

            "location_mentions": [],

            "article_quality": 0,

            "enrichment_confidence": 0,

            "retrieved": False,

            "http_status": status,

            "retrieved_at": datetime.now(UTC)

        }

    soup = BeautifulSoup(

        html,

        "html.parser"

    )

    title = extract_headline(

        soup

    )

    description = extract_description(

        soup

    )

    article = extract_article_text(

        soup

    )

    (
        disaster_keywords,
        matched_keyword,
        hazard_type,
    ) = analyze_disaster_keywords(

        article

    )

    locations = extract_locations(

        article

    )

    analysis = analyze_article(

        title,

        article,

        disaster_keywords,

        locations,

    )

    return {

    **row.to_dict(),

    "article_title": title,

    "article_description": description,

    "article_text": article,

    "article_length": len(article),

    "disaster_keywords": disaster_keywords,

    "matched_keyword": matched_keyword,

    "hazard_type": hazard_type,

    "location_mentions": locations,

    "article_quality": article_quality(

        article,

        disaster_keywords

    ),

    "enrichment_confidence": enrichment_confidence(

        title,

        article,

        disaster_keywords,

        locations

    ),

    "article_score":

        analysis["article_score"],

    "disaster_score":

        analysis["disaster_score"],

    "location_score":

        analysis["location_score"],

    "relevance_score":

        analysis["relevance_score"],

    "retrieved": True,

    "http_status": status,

    "retrieved_at": datetime.now(UTC)

    }
# ==========================================================
# ENRICH DATASET
# ==========================================================

def enrich_dataset(

    df,

    resume=False

):

    session = build_session()

    records = []

    total = len(df)

    for index, (_, row) in enumerate(df.iterrows(), start=1):

        logger.info(

            f"[{index:,}/{total:,}] "

            f"{row['candidate_id']}"

        )

        if resume:

            if pd.notna(

                row.get(

                    "article_text",

                    None

                )

            ):

                records.append(

                    row.to_dict()

                )

                continue

        enriched = build_enriched_record(

            row,

            session

        )

        records.append(

            enriched

        )

        time.sleep(

            SLEEP_SECONDS

        )

    return pd.DataFrame(

        records

    )
# ==========================================================
# WRITE OUTPUTS
# ==========================================================

def write_outputs(

    df,

    export_csv=False

):

    OUTPUT_PARQUET.parent.mkdir(

        parents=True,

        exist_ok=True

    )

    df = df.reindex(

        columns=OUTPUT_COLUMNS

    )

    df.to_parquet(

        OUTPUT_PARQUET,

        index=False

    )

    logger.info(

        f"Parquet written: "

        f"{OUTPUT_PARQUET}"

    )

    if export_csv:

        df.to_csv(

            OUTPUT_CSV,

            index=False

        )

        logger.info(

            f"CSV written: "

            f"{OUTPUT_CSV}"

        )
        # ==========================================================
# SUMMARY
# ==========================================================

def build_summary(df):

    summary = {

        "rows": int(

            len(df)

        ),

        "retrieved": int(

            df["retrieved"].sum()

        ),

        "failed": int(

            (~df["retrieved"]).sum()

        ),

        "avg_article_length": float(

            df["article_length"].mean()

        ),

        "avg_quality": float(

            df["article_quality"].mean()

        ),

        "avg_confidence": float(

            df["enrichment_confidence"].mean()

        ),

        "timestamp":

            datetime.now(

                UTC

            ).isoformat()

    }

    return summary
# ==========================================================
# JSON SAFE
# ==========================================================

def make_json_safe(obj):

    if isinstance(

        obj,

        dict

    ):

        return {

            k: make_json_safe(v)

            for k, v in obj.items()

        }

    if isinstance(

        obj,

        list

    ):

        return [

            make_json_safe(v)

            for v in obj

        ]

    if pd.isna(obj):

        return None

    if isinstance(

        obj,

        pd.Timestamp

    ):

        return obj.isoformat()

    return obj
# ==========================================================
# WRITE SUMMARY
# ==========================================================

def write_summary(summary):

    SUMMARY_JSON.parent.mkdir(

        parents=True,

        exist_ok=True

    )

    with open(

        SUMMARY_JSON,

        "w",

        encoding="utf-8"

    ) as fp:

        json.dump(

            make_json_safe(

                summary

            ),

            fp,

            indent=4

        )

    logger.info(

        f"Summary written: "

        f"{SUMMARY_JSON}"

    )
    # ==========================================================
# MAIN
# ==========================================================

def main():

    start = datetime.now(

        UTC

    )

    args = parse_args()

    print()

    print(

        "=" * 60

    )

    print(

        "ENRICH GDELT ARTICLES"

    )

    print(

        "=" * 60

    )

    df = load_dataset()

    if args.limit:

        df = df.head(

            args.limit

        )

    enriched = enrich_dataset(

        df,

        resume=args.resume

    )

    write_outputs(

        enriched,

        export_csv=args.csv

    )

    summary = build_summary(

        enriched

    )

    write_summary(

        summary

    )

    elapsed = (

        datetime.now(

            UTC

        ) - start

    ).total_seconds()

    print()

    print(

        "=" * 60

    )

    print(

        "ENRICHMENT COMPLETE"

    )

    print(

        "=" * 60

    )

    print(

        f"Rows      : "

        f"{len(enriched):,}"

    )

    print(

        f"Retrieved : "

        f"{summary['retrieved']:,}"

    )

    print(

        f"Failed    : "

        f"{summary['failed']:,}"

    )

    print(

        f"Parquet   : "

        f"{OUTPUT_PARQUET}"

    )

    if args.csv:

        print(

            f"CSV       : "

            f"{OUTPUT_CSV}"

        )

    print(

        f"Summary   : "

        f"{SUMMARY_JSON}"

    )

    print(

        f"Elapsed   : "

        f"{elapsed:.2f}s"

    )


if __name__ == "__main__":

    main()