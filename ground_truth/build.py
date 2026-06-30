"""Build the canonical reviewed disaster-event dataset used for ML labels."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from ground_truth.schemas.ground_truth_schema import GROUND_TRUTH_COLUMNS
from scripts.fusion.models import NORTHEAST_INDIA_BOUNDS, NORTHEAST_INDIA_STATES
from scripts.sources.common.config import PROJECT_ROOT

DEFAULT_INPUTS = [
    PROJECT_ROOT / "data/bronze/ground_truth/gdelt_ground_truth.parquet",
    PROJECT_ROOT / "data/bronze/ground_truth/news_ground_truth.parquet",
    PROJECT_ROOT / "data/bronze/ground_truth/ibtracs_ground_truth.parquet",
    PROJECT_ROOT / "data/bronze/ground_truth/gdacs_ground_truth.parquet",
    PROJECT_ROOT / "data/labels/reviewed_ground_truth.csv",
]
DEFAULT_OUTPUT = PROJECT_ROOT / "data/gold/ground_truth.parquet"
DEFAULT_REVIEW = PROJECT_ROOT / "data/quality/ground_truth_review_queue.csv"
SUPPORTED_HAZARDS = {"FLOOD", "DROUGHT", "CYCLONE"}


def load_sources(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        if not path.exists():
            continue
        frame = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
        frame["_source_file"] = str(path)
        frames.append(frame)
    if not frames:
        raise FileNotFoundError("No ground-truth source files were found.")
    return pd.concat(frames, ignore_index=True, sort=False)


def normalize(events: pd.DataFrame) -> pd.DataFrame:
    result = events.copy()

    def column(name: str, default):
        return result[name] if name in result else pd.Series(default, index=result.index)

    text_columns = {
        "schema_version": "1.0",
        "event_id": "",
        "source": "",
        "source_event_id": "",
        "hazard_subtype": "",
        "severity": "",
        "country": "India",
        "subdistrict": "",
        "village": "",
        "admin_level": "STATE",
        "location_source": "STATE",
        "headline": "",
        "description": "",
        "source_name": "",
        "source_url": "",
    }
    for name, default in text_columns.items():
        result[name] = column(name, default).fillna(default).astype(str).str.strip()

    result["event_date"] = pd.to_datetime(column("event_date", None), utc=True, errors="coerce").dt.normalize()
    result["hazard_type"] = column("hazard_type", "").astype(str).str.upper().str.strip()
    result["state"] = column("state", "").astype(str).str.strip()
    result["district"] = column("district", "").fillna("").astype(str).str.strip()
    for name in (
        "latitude",
        "longitude",
        "fatalities",
        "injured",
        "displaced",
        "affected_population",
        "economic_loss",
    ):
        result[name] = pd.to_numeric(column(name, None), errors="coerce")
    result["confidence"] = pd.to_numeric(column("confidence", 0), errors="coerce").fillna(0)
    verified = column("verified", False).fillna(False)
    if not pd.api.types.is_bool_dtype(verified):
        verified = verified.astype(str).str.lower().isin({"true", "1", "yes", "y"})
    result["verified"] = verified.astype(bool)
    result["collected_at"] = pd.to_datetime(
        column("collected_at", None), utc=True, errors="coerce"
    )
    return result


def build(events: pd.DataFrame, *, minimum_confidence: float = 70.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    result = normalize(events)
    bounds = NORTHEAST_INDIA_BOUNDS
    today = pd.Timestamp.now(tz="UTC").normalize()
    valid = (
        result["verified"]
        & result["hazard_type"].isin(SUPPORTED_HAZARDS)
        & result["state"].isin(NORTHEAST_INDIA_STATES)
        & result["event_date"].between(pd.Timestamp("2000-01-01", tz="UTC"), today)
        & result["latitude"].between(bounds["min_latitude"], bounds["max_latitude"])
        & result["longitude"].between(bounds["min_longitude"], bounds["max_longitude"])
        & (result["confidence"] >= minimum_confidence)
    )
    accepted = result.loc[valid].copy()
    review = result.loc[~valid].copy()
    if not review.empty:
        def reason(row) -> str:
            reasons = []
            if not bool(row["verified"]):
                reasons.append("not_verified")
            if row["hazard_type"] not in SUPPORTED_HAZARDS:
                reasons.append("unsupported_hazard")
            if row["state"] not in NORTHEAST_INDIA_STATES:
                reasons.append("outside_northeast_states")
            if pd.isna(row["event_date"]) or not (
                pd.Timestamp("2000-01-01", tz="UTC") <= row["event_date"] <= today
            ):
                reasons.append("invalid_date")
            if pd.isna(row["latitude"]) or pd.isna(row["longitude"]):
                reasons.append("missing_coordinates")
            elif not (
                bounds["min_latitude"] <= row["latitude"] <= bounds["max_latitude"]
                and bounds["min_longitude"] <= row["longitude"] <= bounds["max_longitude"]
            ):
                reasons.append("outside_region")
            if row["confidence"] < minimum_confidence:
                reasons.append("low_confidence")
            return ";".join(reasons)

        review["review_reason"] = review.apply(reason, axis=1)
    accepted = accepted.sort_values(["event_date", "hazard_type", "state", "district"])
    accepted = accepted.drop_duplicates(
        ["event_date", "hazard_type", "state", "district", "latitude", "longitude"],
        keep="last",
    ).reset_index(drop=True)
    accepted = accepted.reindex(columns=GROUND_TRUTH_COLUMNS)
    return accepted, review


def run(inputs: list[Path], output: Path = DEFAULT_OUTPUT, review_path: Path = DEFAULT_REVIEW) -> dict:
    source = load_sources(inputs)
    accepted, review = build(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    accepted.to_parquet(output, index=False, compression="snappy")
    review.to_csv(review_path, index=False)
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "source_records": len(source),
        "accepted_records": len(accepted),
        "review_records": len(review),
        "hazards": accepted["hazard_type"].value_counts().to_dict(),
        "output": str(output),
        "review_queue": str(review_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    arguments = parser.parse_args()
    report = run(arguments.input or DEFAULT_INPUTS, arguments.output, arguments.review)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
