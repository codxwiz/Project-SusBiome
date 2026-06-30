from __future__ import annotations

import argparse
import io
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from scripts.events.location_utils import (
    normalize_text,
    contains_phrase,
    load_locations,
    searchable_text,
    infer_state,
    infer_district,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_QUEUE_FILE = PROJECT_ROOT / "data/bronze/gdelt/index/download_queue.csv"
DEFAULT_LOCATIONS_FILE = PROJECT_ROOT / "data/raw/locations.csv"

RAW_DIR = PROJECT_ROOT / "data/bronze/gdelt/raw"
BRONZE_OUT = PROJECT_ROOT / "data/bronze/gdelt/parsed_events.csv"
SILVER_OUT = PROJECT_ROOT / "data/silver/events/gdelt_disaster_candidates.csv"
REVIEW_OUT = PROJECT_ROOT / "data/silver/events/gdelt_review_queue.csv"
LOG_OUT = PROJECT_ROOT / "data/bronze/gdelt/logs/gdelt_pipeline_summary.json"


GDELT_COLUMNS = [
    "GLOBALEVENTID",
    "SQLDATE",
    "MonthYear",
    "Year",
    "FractionDate",
    "Actor1Code",
    "Actor1Name",
    "Actor1CountryCode",
    "Actor1KnownGroupCode",
    "Actor1EthnicCode",
    "Actor1Religion1Code",
    "Actor1Religion2Code",
    "Actor1Type1Code",
    "Actor1Type2Code",
    "Actor1Type3Code",
    "Actor2Code",
    "Actor2Name",
    "Actor2CountryCode",
    "Actor2KnownGroupCode",
    "Actor2EthnicCode",
    "Actor2Religion1Code",
    "Actor2Religion2Code",
    "Actor2Type1Code",
    "Actor2Type2Code",
    "Actor2Type3Code",
    "IsRootEvent",
    "EventCode",
    "EventBaseCode",
    "EventRootCode",
    "QuadClass",
    "GoldsteinScale",
    "NumMentions",
    "NumSources",
    "NumArticles",
    "AvgTone",
    "Actor1Geo_Type",
    "Actor1Geo_FullName",
    "Actor1Geo_CountryCode",
    "Actor1Geo_ADM1Code",
    "Actor1Geo_ADM2Code",
    "Actor1Geo_Lat",
    "Actor1Geo_Long",
    "Actor1Geo_FeatureID",
    "Actor2Geo_Type",
    "Actor2Geo_FullName",
    "Actor2Geo_CountryCode",
    "Actor2Geo_ADM1Code",
    "Actor2Geo_ADM2Code",
    "Actor2Geo_Lat",
    "Actor2Geo_Long",
    "Actor2Geo_FeatureID",
    "ActionGeo_Type",
    "ActionGeo_FullName",
    "ActionGeo_CountryCode",
    "ActionGeo_ADM1Code",
    "ActionGeo_ADM2Code",
    "ActionGeo_Lat",
    "ActionGeo_Long",
    "ActionGeo_FeatureID",
    "DATEADDED",
    "SOURCEURL",
]


STATE_ALIASES = {
    "Arunachal Pradesh": [
        "arunachal pradesh",
        "arunachal",
        "itanagar",
    ],
    "Assam": [
        "assam",
        "guwahati",
        "gauhati",
        "brahmaputra",
        "barak valley",
    ],
    "Manipur": [
        "manipur",
        "imphal",
    ],
    "Meghalaya": [
        "meghalaya",
        "shillong",
        "cherrapunji",
        "sohra",
        "mawsynram",
    ],
    "Mizoram": [
        "mizoram",
        "aizawl",
    ],
    "Nagaland": [
        "nagaland",
        "kohima",
        "dimapur",
    ],
    "Sikkim": [
        "sikkim",
        "gangtok",
    ],
    "Tripura": [
        "tripura",
        "agartala",
    ],
}


DISASTER_RULES = {
    "flood": {
        "include": [
            "flood",
            "floods",
            "flooding",
            "flash flood",
            "flash floods",
            "inundation",
            "submerged",
            "waterlogging",
            "water-logging",
            "embankment breach",
            "river overflow",
            "river in spate",
            "landslide",
            "mudslide",
            "glacial lake outburst",
            "glof",
        ],
        "exclude": [
            "flood of support",
            "flood of tourists",
            "flood of messages",
            "flood-control project corruption",
        ],
    },
    "drought": {
        "include": [
            "drought",
            "dry spell",
            "rainfall deficit",
            "water shortage",
            "drinking water crisis",
            "crop failure",
            "monsoon deficit",
            "reservoir storage",
            "scarcity of water",
        ],
        "exclude": [
            "stock market",
            "fuel price",
            "fare hike",
        ],
    },
    "cyclone": {
        "include": [
            "cyclone",
            "cyclonic storm",
            "storm surge",
            "landfall",
            "depression over bay",
            "deep depression",
            "low pressure area",
            "very severe cyclonic storm",
            "extremely severe cyclonic storm",
        ],
        "exclude": [
            "political storm",
            "twitter storm",
            "media storm",
        ],
    },
}


OUTPUT_COLUMNS = [
    "date",
    "state",
    "district",
    "event_type",
    "keyword",
    "confidence_score",
    "needs_review",
    "review_reason",
    "gdelt_event_id",
    "event_code",
    "event_base_code",
    "event_root_code",
    "quad_class",
    "goldstein_scale",
    "num_mentions",
    "num_sources",
    "num_articles",
    "avg_tone",
    "action_geo",
    "action_country",
    "action_lat",
    "action_lon",
    "actor1_name",
    "actor2_name",
    "source_url",
    "source_file",
]


@dataclass
class PipelineStats:
    files_seen: int = 0
    files_parsed: int = 0
    rows_seen: int = 0
    rows_after_india_filter: int = 0
    rows_after_disaster_filter: int = 0
    rows_written: int = 0
    errors: list[str] | None = None

    def to_dict(self) -> dict:
        return {
            "files_seen": self.files_seen,
            "files_parsed": self.files_parsed,
            "rows_seen": self.rows_seen,
            "rows_after_india_filter": self.rows_after_india_filter,
            "rows_after_disaster_filter": self.rows_after_disaster_filter,
            "rows_written": self.rows_written,
            "errors": self.errors or [],
        }


def ensure_dirs() -> None:
    for path in [RAW_DIR, BRONZE_OUT.parent, SILVER_OUT.parent, REVIEW_OUT.parent, LOG_OUT.parent]:
        path.mkdir(parents=True, exist_ok=True)


def parse_gdelt_date(value: object) -> str:
    raw = str(value).strip()
    if not raw or raw.lower() == "nan":
        return ""
    try:
        return datetime.strptime(raw[:8], "%Y%m%d").date().isoformat()
    except ValueError:
        return ""

def read_gdelt_csv_bytes(payload: bytes, source_name: str) -> pd.DataFrame:
    def load_with_separator(separator: str) -> pd.DataFrame:
        return pd.read_csv(
            io.BytesIO(payload),
            sep=separator,
            header=None,
            names=GDELT_COLUMNS,
            dtype=str,
            low_memory=False,
            on_bad_lines="skip",
        )

    df = load_with_separator("\t")

    # Raw GDELT exports are usually TSV, but some project-local files have
    # already been round-tripped through pandas as comma-separated CSV.
    collapsed_rows = (
        len(df.columns) == len(GDELT_COLUMNS)
        and df["SQLDATE"].isna().all()
        and df["GLOBALEVENTID"].fillna("").astype(str).str.contains(",").any()
    )

    if collapsed_rows:
        df = load_with_separator(",")

    if len(df.columns) != len(GDELT_COLUMNS):
        raise ValueError(f"{source_name}: expected {len(GDELT_COLUMNS)} columns, got {len(df.columns)}")

    # Remove header rows accidentally read as data
    df = df[df["GLOBALEVENTID"].astype(str) != "GLOBALEVENTID"]
    df = df[df["GLOBALEVENTID"].astype(str) != "0"]

    # --------------------------------------------------
    # Remove duplicate GDELT events within this source
    # --------------------------------------------------

    before = len(df)

    df = df.drop_duplicates(
        subset=["GLOBALEVENTID"],
        keep="first",
    )

    removed = before - len(df)

    if removed:
        print(
            f"{source_name}: removed {removed:,} duplicate GDELT events"
        )

    df["source_file"] = source_name

    return df


def iter_local_payloads(input_path: Path) -> Iterable[tuple[str, bytes]]:
    if input_path.is_file():
        paths = [input_path]
    else:
        paths = sorted(
            list(input_path.glob("*.zip"))
            + list(input_path.glob("*.CSV"))
            + list(input_path.glob("*.csv"))
        )

    for path in paths:
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path, "r") as archive:
                for member in archive.namelist():
                    if member.lower().endswith((".csv", ".export.csv")):
                        yield member, archive.read(member)
        else:
            yield path.name, path.read_bytes()


def download_payload(url: str, timeout: int = 180) -> list[tuple[str, bytes]]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    filename = url.split("/")[-1] or "gdelt_download"
    payload = response.content

    if filename.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
            return [
                (member, archive.read(member))
                for member in archive.namelist()
                if member.lower().endswith((".csv", ".export.csv"))
            ]

    return [(filename, payload)]


def iter_queue_payloads(queue_file: Path, limit: int | None) -> Iterable[tuple[str, bytes]]:
    queue = pd.read_csv(queue_file)
    if "url" not in queue.columns:
        raise ValueError(f"queue file must contain a url column: {queue_file}")

    if limit is not None:
        queue = queue.head(limit)

    for _, row in queue.iterrows():
        url = str(row["url"])
        for source_name, payload in download_payload(url):
            yield source_name, payload


def filter_india_ne(df: pd.DataFrame) -> pd.DataFrame:
    text = searchable_text(df)

    country_mask = (
        df["ActionGeo_CountryCode"].fillna("").eq("IN")
        | df["Actor1Geo_CountryCode"].fillna("").eq("IN")
        | df["Actor2Geo_CountryCode"].fillna("").eq("IN")
        | df["Actor1CountryCode"].fillna("").eq("IND")
        | df["Actor2CountryCode"].fillna("").eq("IND")
    )

    state_mask = pd.Series(False, index=df.index)
    for aliases in STATE_ALIASES.values():
        for alias in aliases:
            state_mask = state_mask | text.map(lambda item, a=alias: contains_phrase(item, a))

    return df[country_mask & state_mask].copy()


def classify_event(text: str) -> tuple[str, str, int, list[str]]:
    best_type = ""
    best_keyword = ""
    best_score = 0
    reasons: list[str] = []

    for event_type, rules in DISASTER_RULES.items():
        excludes = [phrase for phrase in rules["exclude"] if contains_phrase(text, phrase)]
        if excludes:
            reasons.append(f"{event_type}: excluded phrase {excludes[0]}")
            continue

        matched = [phrase for phrase in rules["include"] if contains_phrase(text, phrase)]
        if not matched:
            continue

        phrase_score = max(len(phrase.split()) for phrase in matched)
        score = 35 + min(25, phrase_score * 5)

        if score > best_score:
            best_type = event_type
            best_keyword = sorted(matched, key=len, reverse=True)[0]
            best_score = score

    return best_type, best_keyword, best_score, reasons


def to_numeric(value: object) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def build_candidates(df: pd.DataFrame, locations: pd.DataFrame, min_score: int) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    text_series = searchable_text(df)
    rows: list[dict] = []

    for idx, record in df.iterrows():
        text = text_series.loc[idx]

        event_type, keyword, disaster_score, rejection_reasons = classify_event(text)

        # --------------------------------------------------
        # Fallback classification using URL only
        # --------------------------------------------------

        if not event_type:
            url = normalize_text(record.get("SOURCEURL", ""))

            for disaster, rules in DISASTER_RULES.items():
                for phrase in rules["include"]:
                    if contains_phrase(url, phrase):
                        event_type = disaster
                        keyword = phrase
                        disaster_score = 40
                        break
                if event_type:
                    break

        if not event_type:
            continue

        state, state_hits = infer_state(text)
        district = infer_district(text, state, locations)

        score = disaster_score
        review_reason: list[str] = []

        if state != "UNKNOWN":
            score += min(20, state_hits * 8)
        else:
            review_reason.append("state_not_found")

        if district != "UNKNOWN":
            score += 15
        else:
            review_reason.append("district_not_found")

        if str(record.get("ActionGeo_CountryCode", "")) == "IN":
            score += 10
        else:
            review_reason.append("action_geo_not_india")

        if str(record.get("ActionGeo_FullName", "")).strip():
            score += 5

        if str(record.get("SOURCEURL", "")).strip():
            score += 5
        else:
            review_reason.append("missing_source_url")

        if rejection_reasons:
            review_reason.extend(rejection_reasons)

        score = min(score, 100)
        if score < min_score:
            continue

        needs_review = score < 80 or district == "UNKNOWN"

        if score >= min_score:
            print()
            print("=" * 80)
            print("Candidate Found")
            print("-" * 80)
            print("Type :", event_type)
            print("State:", state)
            print("District:", district)
            print("Keyword:", keyword)
            print("Score:", score)
            print("Geo:", record.get("ActionGeo_FullName", ""))
            print("URL:", record.get("SOURCEURL", ""))
            print("=" * 80)

        rows.append(
            {
                "date": parse_gdelt_date(record.get("SQLDATE")),
                "state": state,
                "district": district,
                "event_type": event_type,
                "keyword": keyword,
                "confidence_score": score,
                "needs_review": needs_review,
                "review_reason": ";".join(review_reason),
                "gdelt_event_id": record.get("GLOBALEVENTID", ""),
                "event_code": record.get("EventCode", ""),
                "event_base_code": record.get("EventBaseCode", ""),
                "event_root_code": record.get("EventRootCode", ""),
                "quad_class": record.get("QuadClass", ""),
                "goldstein_scale": to_numeric(record.get("GoldsteinScale")),
                "num_mentions": to_numeric(record.get("NumMentions")),
                "num_sources": to_numeric(record.get("NumSources")),
                "num_articles": to_numeric(record.get("NumArticles")),
                "avg_tone": to_numeric(record.get("AvgTone")),
                "action_geo": record.get("ActionGeo_FullName", ""),
                "action_country": record.get("ActionGeo_CountryCode", ""),
                "action_lat": to_numeric(record.get("ActionGeo_Lat")),
                "action_lon": to_numeric(record.get("ActionGeo_Long")),
                "actor1_name": record.get("Actor1Name", ""),
                "actor2_name": record.get("Actor2Name", ""),
                "source_url": record.get("SOURCEURL", ""),
                "source_file": record.get("source_file", ""),
            }
        )

    out = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

    if out.empty:
        return out

    out = out.drop_duplicates(
        subset=["date", "state", "district", "event_type", "source_url"],
        keep="first",
    )

    out = out.sort_values(
        ["date", "state", "district", "event_type", "confidence_score"],
        ascending=[False, True, True, True, False],
    )

    return out


def write_dataset(path: Path, df: pd.DataFrame) -> None:
    """
    Always overwrite pipeline outputs.

    Pipeline outputs are deterministic and should never
    accumulate rows across executions.
    """

    df.to_csv(path, index=False)


def run_pipeline(
    input_path: Path | None,
    queue_file: Path | None,
    locations_file: Path,
    limit: int | None,
    min_score: int,
) -> PipelineStats:
    ensure_dirs()

    stats = PipelineStats(errors=[])
    locations = load_locations(locations_file)

    payload_iter: Iterable[tuple[str, bytes]]
    if input_path is not None:
        payload_iter = iter_local_payloads(input_path)
    elif queue_file is not None:
        payload_iter = iter_queue_payloads(queue_file, limit)
    else:
        raise ValueError("Provide either input_path or queue_file")

    bronze_frames: list[pd.DataFrame] = []
    candidate_frames: list[pd.DataFrame] = []

    for source_name, payload in payload_iter:
        stats.files_seen += 1

        try:
            df = read_gdelt_csv_bytes(payload, source_name)
            stats.files_parsed += 1
            stats.rows_seen += len(df)

            india_ne = filter_india_ne(df)
            stats.rows_after_india_filter += len(india_ne)

            candidates = build_candidates(india_ne, locations, min_score)
            stats.rows_after_disaster_filter += len(candidates)

            if not india_ne.empty:
                bronze_frames.append(india_ne)

            if not candidates.empty:
                candidate_frames.append(candidates)

            print(
                f"{source_name}: rows={len(df):,}, "
                f"ne_india={len(india_ne):,}, "
                f"candidates={len(candidates):,}"
            )

        except Exception as exc:
            message = f"{source_name}: {exc}"
            stats.errors.append(message)
            print(f"ERROR: {message}")

    bronze = pd.concat(bronze_frames, ignore_index=True) if bronze_frames else pd.DataFrame(columns=GDELT_COLUMNS)
    bronze = bronze.sort_values(
    "GLOBALEVENTID"
)

    bronze = bronze.drop_duplicates(
    subset=["GLOBALEVENTID"],
    keep="first",
)
    candidates = pd.concat(candidate_frames, ignore_index=True) if candidate_frames else pd.DataFrame(columns=OUTPUT_COLUMNS)

    if not candidates.empty:
        candidates = candidates.drop_duplicates(
            subset=[
    "gdelt_event_id",
    "source_url",
],
            keep="first",
        )
        candidates = candidates.sort_values(
            ["date", "state", "district", "event_type", "confidence_score"],
            ascending=[False, True, True, True, False],
        )

    review = candidates[candidates["needs_review"].astype(bool)].copy() if not candidates.empty else candidates.copy()

    write_dataset(BRONZE_OUT, bronze)
    write_dataset(SILVER_OUT, candidates)
    write_dataset(REVIEW_OUT, review)

    stats.rows_written = len(candidates)

    LOG_OUT.write_text(json.dumps(stats.to_dict(), indent=2), encoding="utf-8")

    print("\nGDELT pipeline complete")
    print(f"Bronze parsed events : {BRONZE_OUT}")
    print(f"Silver candidates    : {SILVER_OUT}")
    print(f"Review queue         : {REVIEW_OUT}")
    print(f"Summary log          : {LOG_OUT}")

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Production GDELT disaster-event parser for SusBiome."
    )

    parser.add_argument(
        "--input-path",
        type=Path,
        default=None,
        help="Local .CSV/.zip file or directory of GDELT files. If omitted, --queue-file is used.",
    )

    parser.add_argument(
        "--queue-file",
        type=Path,
        default=DEFAULT_QUEUE_FILE,
        help="CSV queue with a url column for GDELT downloads.",
    )

    parser.add_argument(
        "--locations-file",
        type=Path,
        default=DEFAULT_LOCATIONS_FILE,
        help="District/state location CSV used for district matching.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of queue rows when downloading.",
    )

    parser.add_argument(
        "--min-score",
        type=int,
        default=55,
        help="Minimum parser confidence score to keep a candidate.",
    )

    parser.add_argument(
        "--no-queue",
        action="store_true",
        help="Disable queue fallback. Requires --input-path.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    queue_file = None if args.no_queue else args.queue_file

    run_pipeline(
        input_path=args.input_path,
        queue_file=queue_file,
        locations_file=args.locations_file,
        limit=args.limit,
        min_score=args.min_score,
    )


if __name__ == "__main__":
    main()
