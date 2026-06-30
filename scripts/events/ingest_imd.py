import argparse
import hashlib
import json
import logging
import time

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests
from bs4 import BeautifulSoup
# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = (

    Path(__file__).resolve().parents[2]

)

DATA_DIR = PROJECT_ROOT / "data"

BRONZE_DIR = DATA_DIR / "bronze" / "imd"

RAW_DIR = BRONZE_DIR / "raw"

HTML_DIR = BRONZE_DIR / "html"

PDF_DIR = BRONZE_DIR / "pdf"

METADATA_DIR = BRONZE_DIR / "metadata"

LOG_DIR = BRONZE_DIR / "logs"
RAW_PARQUET = BRONZE_DIR / "imd_raw.parquet"

RAW_CSV = BRONZE_DIR / "imd_raw.csv"

SUMMARY_JSON = (

    LOG_DIR /

    "ingest_imd_summary.json"

)
# ==========================================================
# CREATE DIRECTORIES
# ==========================================================

for directory in (

    BRONZE_DIR,

    RAW_DIR,

    HTML_DIR,

    PDF_DIR,

    METADATA_DIR,

    LOG_DIR,

):

    directory.mkdir(

        parents=True,

        exist_ok=True

    )
    # ==========================================================
# IMD SOURCES
# ==========================================================

# ==========================================================
# IMD SOURCE REGISTRY
# ==========================================================

IMD_SOURCES = [

    {

        # -----------------------------
        # Identity
        # -----------------------------

        "id": "imd_daily_weather",

        "name": "Daily Weather Bulletin",

        "category": "weather",

        "hazard_types": [

            "FLOOD",
            "HEAVY_RAIN",
            "HEATWAVE",
            "COLD_WAVE"

        ],

        # -----------------------------
        # Download
        # -----------------------------

        "url": "",

        "content_type": "html",

        "method": "GET",

        "encoding": "utf-8",

        "timeout": 30,

        "retries": 3,

        # -----------------------------
        # Storage
        # -----------------------------

        "folder": "html",

        "extension": ".html",

        # -----------------------------
        # Parsing
        # -----------------------------

        "parser": "imd_html",

        "expected_format": "bulletin",

        # -----------------------------
        # Refresh
        # -----------------------------

        "refresh": "daily",

        "priority": 1,

    },

    {

        "id": "imd_heavy_rainfall",

        "name": "Heavy Rainfall Warning",

        "category": "warning",

        "hazard_types": [

            "FLOOD",

            "LANDSLIDE"

        ],

        "url": "",

        "content_type": "html",

        "method": "GET",

        "encoding": "utf-8",

        "timeout": 30,

        "retries": 3,

        "folder": "html",

        "extension": ".html",

        "parser": "imd_warning",

        "expected_format": "warning",

        "refresh": "6h",

        "priority": 1,

    },

    {

        "id": "imd_cyclone",

        "name": "Cyclone Bulletin",

        "category": "cyclone",

        "hazard_types": [

            "CYCLONE"

        ],

        "url": "",

        "content_type": "html",

        "method": "GET",

        "encoding": "utf-8",

        "timeout": 30,

        "retries": 3,

        "folder": "html",

        "extension": ".html",

        "parser": "imd_cyclone",

        "expected_format": "bulletin",

        "refresh": "3h",

        "priority": 1,

    }

]
OUTPUT_COLUMNS = [

    "document_id",

    "source",

    "bulletin_type",

    "url",

    "filename",

    "content_type",

    "http_status",

    "published_time",

    "download_time",

    "sha256",

    "etag",

    "size_bytes",

    "retrieved",

]
# ==========================================================
# LOGGING
# ==========================================================

logger = logging.getLogger(

    "imd_ingest"

)

logger.setLevel(

    logging.INFO

)

formatter = logging.Formatter(

    "%(asctime)s | %(levelname)s | %(message)s"

)

console = logging.StreamHandler()

console.setFormatter(

    formatter

)

logger.addHandler(

    console

)
def parse_args():

    parser = argparse.ArgumentParser(

        description="Download IMD bulletins."

    )

    parser.add_argument(

        "--csv",

        action="store_true",

        help="Write CSV output."

    )

    parser.add_argument(

        "--force",

        action="store_true",

        help="Redownload existing files."

    )

    parser.add_argument(

        "--timeout",

        type=int,

        default=30,

    )

    parser.add_argument(

        "--retries",

        type=int,

        default=3,

    )

    parser.add_argument(

        "--limit",

        type=int,

    )

    return parser.parse_args()
# ==========================================================
# HTTP SESSION
# ==========================================================

def build_session():

    session = requests.Session()

    session.headers.update({

        "User-Agent": (

            "SusBiome/1.0 "

            "(Research Platform)"

        ),

        "Accept":

            "*/*",

        "Accept-Encoding":

            "gzip, deflate",

        "Connection":

            "keep-alive",

    })

    return session
# ==========================================================
# SHA256
# ==========================================================

def sha256_bytes(data):

    return hashlib.sha256(

        data

    ).hexdigest()
# ==========================================================
# BUILD LOCAL FILENAME
# ==========================================================

def build_filename(

    source,

    content_type,

):

    timestamp = datetime.now(

        UTC

    ).strftime(

        "%Y%m%d_%H%M%S"

    )

    ext = source["extension"]

    return (

        f"{source['id']}_"

        f"{timestamp}"

        f"{ext}"

    )
# ==========================================================
# SAVE RAW FILE
# ==========================================================

def save_raw_file(

    source,

    filename,

    content,

):

    folder = {

        "html": HTML_DIR,

        "pdf": PDF_DIR,

    }[

        source["folder"]

    ]

    path = folder / filename

    path.write_bytes(

        content

    )

    return path
# ==========================================================
# DOWNLOAD SOURCE
# ==========================================================

def download_source(

    session,

    source,

):

    logger.info(

        f"Downloading "

        f"{source['name']}"

    )

    response = session.get(

        source["url"],

        timeout=source["timeout"]

    )

    response.raise_for_status()

    content = response.content

    filename = build_filename(

        source,

        response.headers.get(

            "Content-Type",

            ""

        )

    )

    filepath = save_raw_file(

        source,

        filename,

        content,

    )

    return {

        "document_id":

            sha256_bytes(content),

        "source":

            source["id"],

        "bulletin_type":

            source["category"],

        "url":

            source["url"],

        "filename":

            filename,

        "content_type":

            response.headers.get(

                "Content-Type"

            ),

        "http_status":

            response.status_code,

        "published_time":

            None,

        "download_time":

            datetime.now(

                UTC

            ),

        "sha256":

            sha256_bytes(

                content

            ),

        "etag":

            response.headers.get(

                "ETag"

            ),

        "size_bytes":

            len(content),

        "retrieved":

            True,

    }
# ==========================================================
# DOWNLOAD WITH RETRY
# ==========================================================

def download_with_retry(

    session,

    source,

):

    last_error = None

    for attempt in range(

        source["retries"]

    ):

        try:

            return download_source(

                session,

                source,

            )

        except Exception as exc:

            last_error = exc

            logger.warning(

                f"{source['name']} "

                f"(attempt {attempt+1}) "

                f"failed: {exc}"

            )

            time.sleep(

                2 ** attempt

            )

    logger.error(

        f"{source['name']} failed."

    )

    return {

        "document_id": None,

        "source": source["id"],

        "bulletin_type": source["category"],

        "url": source["url"],

        "filename": None,

        "content_type": None,

        "http_status": None,

        "published_time": None,

        "download_time": datetime.now(UTC),

        "sha256": None,

        "etag": None,

        "size_bytes": 0,

        "retrieved": False,

        "error": str(last_error),

    }
# ==========================================================
# WRITE OUTPUT
# ==========================================================

def write_outputs(

    df,

    export_csv=False,

):

    table = pa.Table.from_pandas(

        df,

        preserve_index=False,

    )

    pq.write_table(

        table,

        RAW_PARQUET,

        compression="snappy",

    )

    logger.info(

        f"Parquet written: {RAW_PARQUET}"

    )

    if export_csv:

        df.to_csv(

            RAW_CSV,

            index=False,

        )

        logger.info(

            f"CSV written: {RAW_CSV}"

        )
        # ==========================================================
# BUILD SUMMARY
# ==========================================================

def build_summary(df):

    return {

        "documents":

            int(len(df)),

        "retrieved":

            int(df["retrieved"].sum()),

        "failed":

            int((~df["retrieved"]).sum()),

        "created_at":

            datetime.now(UTC).isoformat(),

    }
# ==========================================================
# WRITE SUMMARY
# ==========================================================

def write_summary(

    summary,

):

    with open(

        SUMMARY_JSON,

        "w",

        encoding="utf-8",

    ) as f:

        json.dump(

            summary,

            f,

            indent=2,

        )

    logger.info(

        f"Summary written: {SUMMARY_JSON}"

    )
    # ==========================================================
# MAIN
# ==========================================================

def main():

    start = time.time()

    args = parse_args()

    logger.info(

        "=" * 60

    )

    logger.info(

        "INGEST IMD"

    )

    logger.info(

        "=" * 60

    )

    session = build_session()

    rows = []

    sources = IMD_SOURCES

    if args.limit:

        sources = sources[:args.limit]

    for source in sources:

        rows.append(

            download_with_retry(

                session,

                source,

            )

        )

    df = pd.DataFrame(

        rows,

        columns=OUTPUT_COLUMNS,

    )

    write_outputs(

        df,

        export_csv=args.csv,

    )

    summary = build_summary(

        df,

    )

    write_summary(

        summary,

    )

    logger.info(

        "=" * 60

    )

    logger.info(

        "INGESTION COMPLETE"

    )

    logger.info(

        "=" * 60

    )

    logger.info(

        f"Rows      : {len(df)}"

    )

    logger.info(

        f"Retrieved : {summary['retrieved']}"

    )

    logger.info(

        f"Failed    : {summary['failed']}"

    )

    logger.info(

        f"Elapsed   : {time.time()-start:.2f}s"

    )


if __name__ == "__main__":

    main()