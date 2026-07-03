"""Create a compact owner review queue for public flood and cyclone claims."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from scripts.sources.common.config import PROJECT_ROOT

GROUND_TRUTH_PATH = PROJECT_ROOT / "data/gold/ground_truth.parquet"
OUTPUT_PATH = PROJECT_ROOT / "data/quality/production_event_review.csv"
SUMMARY_PATH = PROJECT_ROOT / "data/quality/production_event_review.json"


def _spread(frame: pd.DataFrame, count: int) -> pd.DataFrame:
    if count < 1:
        raise ValueError("Review count must be positive.")
    if len(frame) <= count:
        return frame
    if count == 1:
        return frame.iloc[[0]]
    positions = sorted(
        {round(index * (len(frame) - 1) / (count - 1)) for index in range(count)}
    )
    return frame.iloc[positions]


def build(count_per_hazard: int = 15) -> dict:
    events = pd.read_parquet(GROUND_TRUTH_PATH)
    events = events.loc[
        events["verified"].fillna(False) & events["hazard_type"].isin(["FLOOD", "CYCLONE"])
    ].copy()
    events["event_date"] = pd.to_datetime(events["event_date"], utc=True).dt.date.astype(str)
    events = events.sort_values(["hazard_type", "event_date", "state", "district"])
    selections = []
    for hazard in ("FLOOD", "CYCLONE"):
        candidates = events.loc[events["hazard_type"].eq(hazard)].drop_duplicates(
            ["event_date", "state", "district", "source_event_id"]
        )
        selections.append(_spread(candidates, count_per_hazard))
    review = pd.concat(selections, ignore_index=True)
    columns = [
        "event_date", "hazard_type", "state", "district", "source", "source_event_id",
        "headline", "source_url", "confidence",
    ]
    review = review[columns].rename(columns={"confidence": "current_confidence"})
    review["review_status"] = "PENDING"
    review["event_occurred_in_district"] = ""
    review["date_correct"] = ""
    review["reviewer_notes"] = ""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_PATH.with_suffix(".csv.tmp")
    review.to_csv(temporary, index=False)
    os.replace(temporary, OUTPUT_PATH)
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "rows": len(review),
        "hazards": review["hazard_type"].value_counts().to_dict(),
        "states": sorted(review["state"].unique().tolist()),
        "instructions": (
            "Set review_status to APPROVED or REJECTED and complete the two correctness columns."
        ),
        "output": str(OUTPUT_PATH),
    }
    SUMMARY_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count-per-hazard", type=int, default=15)
    arguments = parser.parse_args()
    print(json.dumps(build(arguments.count_per_hazard), indent=2))


if __name__ == "__main__":
    main()
