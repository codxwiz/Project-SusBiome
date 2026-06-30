"""Align verified disaster events to daily Northeast India weather grid cells."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from scripts.fusion.models import NORTHEAST_INDIA_STATES
from scripts.sources.common.config import PROJECT_ROOT

FUSION_ROOT = PROJECT_ROOT / "data/fusion/historical"
OUTPUT_ROOT = PROJECT_ROOT / "data/gold/training"
QUALITY_ROOT = PROJECT_ROOT / "data/quality"

TARGETS = {
    "FLOOD": "flood_risk",
    "DROUGHT": "drought_risk",
    "CYCLONE": "cyclone_risk",
}
WINDOW_DAYS = {"FLOOD": 1, "DROUGHT": 30, "CYCLONE": 2}


@dataclass(frozen=True, slots=True)
class AlignmentReport:
    input_events: int
    accepted_events: int
    rejected_events: int
    matched_rows: int


def prepare_events(events: pd.DataFrame, *, minimum_confidence: float = 70.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"event_date", "hazard_type", "state", "latitude", "longitude", "verified"}
    missing = required - set(events.columns)
    if missing:
        raise ValueError("Ground truth is missing: " + ", ".join(sorted(missing)))
    prepared = events.copy()
    prepared["event_date"] = pd.to_datetime(prepared["event_date"], utc=True, errors="coerce").dt.normalize()
    prepared["hazard_type"] = prepared["hazard_type"].astype(str).str.upper()
    prepared["confidence"] = pd.to_numeric(prepared.get("confidence", 100), errors="coerce").fillna(0)
    accepted = (
        prepared["verified"].astype(bool)
        & prepared["hazard_type"].isin(TARGETS)
        & prepared["state"].isin(NORTHEAST_INDIA_STATES)
        & prepared["event_date"].notna()
        & prepared["latitude"].notna()
        & prepared["longitude"].notna()
        & (prepared["confidence"] >= minimum_confidence)
    )
    rejected = prepared.loc[~accepted].copy()
    prepared = prepared.loc[accepted].copy()
    prepared["latitude"] = (pd.to_numeric(prepared["latitude"]) / 0.25).round() * 0.25
    prepared["longitude"] = (pd.to_numeric(prepared["longitude"]) / 0.25).round() * 0.25
    return prepared, rejected


def align_events(weather: pd.DataFrame, events: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    result = weather.copy()
    result["valid_time"] = pd.to_datetime(result["valid_time"], utc=True).dt.normalize()
    for target in TARGETS.values():
        result[target] = 0
        result[target.replace("_risk", "_event_group")] = ""
    matched = pd.Series(False, index=result.index)
    for event in events.itertuples(index=False):
        hazard = str(event.hazard_type)
        target = TARGETS[hazard]
        window = WINDOW_DAYS[hazard]
        event_date = pd.Timestamp(event.event_date)
        mask = (
            result["latitude"].eq(float(event.latitude))
            & result["longitude"].eq(float(event.longitude))
            & result["valid_time"].between(
                event_date - pd.Timedelta(days=window),
                event_date + pd.Timedelta(days=window),
            )
        )
        result.loc[mask, target] = 1
        group_column = target.replace("_risk", "_event_group")
        source_event_id = str(getattr(event, "source_event_id", "") or "").strip()
        event_id = str(getattr(event, "event_id", "") or "").strip()
        result.loc[mask, group_column] = source_event_id or event_id
        matched |= mask
    result["label_method"] = "verified_event_alignment"
    return result, int(matched.sum())


def run(events_path: Path, *, start_year: int, end_year: int) -> AlignmentReport:
    events = pd.read_parquet(events_path) if events_path.suffix == ".parquet" else pd.read_csv(events_path)
    accepted, rejected = prepare_events(events)
    QUALITY_ROOT.mkdir(parents=True, exist_ok=True)
    rejected.to_csv(QUALITY_ROOT / "ground_truth_review_queue.csv", index=False)
    matched_rows = 0
    for year in range(start_year, end_year + 1):
        source = FUSION_ROOT / f"year={year:04d}" / "weather.parquet"
        if not source.exists():
            continue
        weather = pd.read_parquet(source)
        yearly_events = accepted[accepted["event_date"].dt.year.between(year - 1, year + 1)]
        aligned, matched = align_events(weather, yearly_events)
        matched_rows += matched
        destination = OUTPUT_ROOT / f"year={year:04d}" / "training.parquet"
        destination.parent.mkdir(parents=True, exist_ok=True)
        aligned.to_parquet(destination, index=False, compression="snappy")
    report = AlignmentReport(len(events), len(accepted), len(rejected), matched_rows)
    (QUALITY_ROOT / "label_alignment_summary.json").write_text(
        json.dumps(report.__dict__ if hasattr(report, "__dict__") else {
            "input_events": report.input_events,
            "accepted_events": report.accepted_events,
            "rejected_events": report.rejected_events,
            "matched_rows": report.matched_rows,
        }, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--start-year", type=int, default=2006)
    parser.add_argument("--end-year", type=int, default=2025)
    arguments = parser.parse_args()
    print(run(arguments.events, start_year=arguments.start_year, end_year=arguments.end_year))


if __name__ == "__main__":
    main()
