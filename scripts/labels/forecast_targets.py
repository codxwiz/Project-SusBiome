"""Create leakage-safe future disaster targets over historical feature partitions."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from scripts.sources.common.config import PROJECT_ROOT

FEATURE_ROOT = PROJECT_ROOT / "data/gold/features_historical"
GROUND_TRUTH_PATH = PROJECT_ROOT / "data/gold/ground_truth.parquet"
OUTPUT_ROOT = PROJECT_ROOT / "data/gold/forecast_targets"
SUMMARY_PATH = PROJECT_ROOT / "data/quality/forecast_target_summary.json"
HORIZONS = (3, 7, 14)
PRODUCTION_HAZARDS = {"FLOOD": "flood", "CYCLONE": "cyclone"}
GRID = ["latitude", "longitude"]


@dataclass(slots=True, frozen=True)
class TargetSummary:
    years: int
    rows: int
    events: int
    independent_events: dict[str, int]
    positive_rows: dict[str, int]
    output: str


def prepare_events(events: pd.DataFrame) -> pd.DataFrame:
    required = {
        "event_date", "hazard_type", "latitude", "longitude", "verified",
        "source", "source_event_id", "event_id",
    }
    missing = required - set(events.columns)
    if missing:
        raise ValueError("Ground truth is missing: " + ", ".join(sorted(missing)))
    prepared = events.copy()
    prepared["event_date"] = pd.to_datetime(
        prepared["event_date"], utc=True, errors="coerce"
    ).dt.normalize()
    prepared["hazard_type"] = prepared["hazard_type"].astype(str).str.upper()
    prepared = prepared.loc[
        prepared["verified"].astype(bool)
        & prepared["hazard_type"].isin(PRODUCTION_HAZARDS)
        & prepared["event_date"].notna()
        & prepared["latitude"].notna()
        & prepared["longitude"].notna()
    ].copy()
    prepared["latitude"] = (pd.to_numeric(prepared["latitude"]) / 0.25).round() * 0.25
    prepared["longitude"] = (pd.to_numeric(prepared["longitude"]) / 0.25).round() * 0.25
    source_ids = prepared["source_event_id"].fillna("").astype(str).str.strip()
    event_ids = prepared["event_id"].fillna("").astype(str).str.strip()
    prepared["event_group"] = source_ids.where(source_ids.ne(""), event_ids)
    if prepared["event_group"].eq("").any():
        raise ValueError("Every production event must have an independent event identifier.")
    return prepared


def expanded_target_keys(
    events: pd.DataFrame,
    *,
    hazard: str,
    horizon_days: int,
) -> pd.DataFrame:
    selected = events.loc[events["hazard_type"].eq(hazard)].copy()
    rows = []
    for event in selected.itertuples(index=False):
        # Features at issue_date may only use information available before event_date.
        for lead_day in range(1, horizon_days + 1):
            rows.append(
                {
                    "latitude": float(event.latitude),
                    "longitude": float(event.longitude),
                    "valid_time": pd.Timestamp(event.event_date) - pd.Timedelta(days=lead_day),
                    "event_group": str(event.event_group),
                    "lead_days": lead_day,
                }
            )
    if not rows:
        return pd.DataFrame(
            columns=[*GRID, "valid_time", "event_group", "lead_days"]
        )
    expanded = pd.DataFrame(rows)
    return (
        expanded.sort_values([*GRID, "valid_time", "lead_days"])
        .drop_duplicates([*GRID, "valid_time", "event_group"])
        .reset_index(drop=True)
    )


def add_future_targets(features: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    result = features.copy()
    result["valid_time"] = pd.to_datetime(result["valid_time"], utc=True).dt.normalize()
    feature_index = pd.MultiIndex.from_frame(result[[*GRID, "valid_time"]])
    for hazard_name, prefix in PRODUCTION_HAZARDS.items():
        for horizon in HORIZONS:
            target = f"{prefix}_risk_{horizon}d"
            group_column = f"{prefix}_event_group_{horizon}d"
            lead_column = f"{prefix}_lead_days_{horizon}d"
            keys = expanded_target_keys(events, hazard=hazard_name, horizon_days=horizon)
            if keys.empty:
                result[target] = 0
                result[group_column] = ""
                result[lead_column] = pd.NA
                continue
            key_index = pd.MultiIndex.from_frame(keys[[*GRID, "valid_time"]])
            result[target] = feature_index.isin(key_index).astype("int8")
            group_map = (
                keys.groupby([*GRID, "valid_time"], sort=False)["event_group"]
                .agg(lambda values: "|".join(sorted(set(values))))
            )
            lead_map = keys.groupby([*GRID, "valid_time"], sort=False)["lead_days"].min()
            result[group_column] = feature_index.map(group_map).fillna("")
            result[lead_column] = feature_index.map(lead_map).astype("Int16")
    result["label_method"] = "verified_future_event_alignment"
    return result


def build(
    *,
    feature_root: Path = FEATURE_ROOT,
    ground_truth_path: Path = GROUND_TRUTH_PATH,
    output_root: Path = OUTPUT_ROOT,
) -> TargetSummary:
    events = prepare_events(pd.read_parquet(ground_truth_path))
    feature_files = sorted(feature_root.glob("year=*/features.parquet"))
    if not feature_files:
        raise FileNotFoundError(f"No feature partitions under {feature_root}")
    positive_rows = {
        f"{prefix}_risk_{horizon}d": 0
        for prefix in PRODUCTION_HAZARDS.values()
        for horizon in HORIZONS
    }
    total_rows = 0
    for source in feature_files:
        year = int(source.parent.name.split("=", 1)[1])
        features = pd.read_parquet(source)
        relevant = events.loc[
            events["event_date"].dt.year.between(year, year + 1)
        ]
        targeted = add_future_targets(features, relevant)
        destination = output_root / f"year={year:04d}" / "features.parquet"
        destination.parent.mkdir(parents=True, exist_ok=True)
        targeted.to_parquet(destination, index=False, compression="snappy")
        total_rows += len(targeted)
        for target in positive_rows:
            positive_rows[target] += int(targeted[target].sum())
    independent = {
        prefix: int(events.loc[events["hazard_type"].eq(hazard), "event_group"].nunique())
        for hazard, prefix in PRODUCTION_HAZARDS.items()
    }
    summary = TargetSummary(
        years=len(feature_files),
        rows=total_rows,
        events=len(events),
        independent_events=independent,
        positive_rows=positive_rows,
        output=str(output_root),
    )
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "status"), nargs="?", default="build")
    arguments = parser.parse_args()
    if arguments.command == "build":
        result = asdict(build())
    else:
        if not SUMMARY_PATH.exists():
            raise SystemExit("Forecast target summary does not exist.")
        result = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
