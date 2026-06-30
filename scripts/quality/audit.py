from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from scripts.fusion.models import NORTHEAST_INDIA_BOUNDS
from scripts.ml.models import (
    FEATURE_COLUMNS,
    EXPERIMENTAL_TARGET_COLUMNS,
    MIN_HISTORY_DAYS,
    MIN_POSITIVE_SAMPLES,
    PRODUCTION_TARGET_COLUMNS,
    TARGET_COLUMNS,
    TRAINING_DATASET,
)
from scripts.prediction.loader import PredictionLoader
from scripts.sources.common.config import PROJECT_ROOT
from scripts.ingestion.historical_weather import GPM_EXPECTED_DAYS

MIN_INDEPENDENT_EVENTS = 10


@dataclass(frozen=True, slots=True)
class Finding:
    severity: str
    check: str
    message: str


def audit_training(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not path.exists():
        return [Finding("ERROR", "training.exists", f"Missing dataset: {path}")]

    files = [path] if path.is_file() else sorted(path.glob("year=*/features.parquet"))
    if not files:
        return [Finding("ERROR", "training.exists", f"No training partitions under: {path}")]

    required_columns = [
        "latitude",
        "longitude",
        "valid_time",
        "label_method",
        *FEATURE_COLUMNS,
        *PRODUCTION_TARGET_COLUMNS,
    ]
    columns = [*required_columns, *EXPERIMENTAL_TARGET_COLUMNS]
    import pyarrow.parquet as pq

    available = set(pq.ParquetFile(files[0]).schema.names)

    missing_required = [column for column in required_columns if column not in available]
    missing_experimental = [
        column for column in EXPERIMENTAL_TARGET_COLUMNS if column not in available
    ]
    if missing_required:
        findings.append(
            Finding(
                "ERROR",
                "training.schema",
                "Missing: " + ", ".join(missing_required),
            )
        )
    if missing_experimental:
        findings.append(
            Finding(
                "WARNING",
                "training.experimental_schema",
                "Missing: " + ", ".join(missing_experimental),
            )
        )
    columns = [column for column in columns if column in available]

    all_dates: set[pd.Timestamp] = set()
    outside_rows = 0
    nulls = 0
    methods: set[str] = set()
    target_counts = {target: {0: 0, 1: 0} for target in TARGET_COLUMNS}
    bounds = NORTHEAST_INDIA_BOUNDS
    for file in files:
        dataframe = pd.read_parquet(file, columns=columns)
        dates = pd.to_datetime(dataframe["valid_time"], utc=True, errors="coerce")
        all_dates.update(dates.dt.normalize().dropna().tolist())
        outside = ~(
            dataframe["latitude"].between(bounds["min_latitude"], bounds["max_latitude"])
            & dataframe["longitude"].between(
                bounds["min_longitude"], bounds["max_longitude"]
            )
        )
        outside_rows += int(outside.sum())
        present_features = [column for column in FEATURE_COLUMNS if column in dataframe]
        nulls += int(dataframe[present_features].isna().sum().sum())
        if "label_method" in dataframe:
            methods.update(dataframe["label_method"].dropna().astype(str).unique())
        for target in TARGET_COLUMNS:
            if target in dataframe:
                counts = dataframe[target].value_counts().to_dict()
                target_counts[target][0] += int(counts.get(0, 0))
                target_counts[target][1] += int(counts.get(1, 0))

    days = len(all_dates)
    if days < MIN_HISTORY_DAYS:
        findings.append(
            Finding(
                "ERROR",
                "training.history",
                f"Found {days} distinct days; require at least {MIN_HISTORY_DAYS}.",
            )
        )

    if outside_rows:
        findings.append(
            Finding(
                "ERROR",
                "training.geography",
                f"{outside_rows} rows are outside Northeast India.",
            )
        )

    if nulls:
        findings.append(
            Finding("ERROR", "training.completeness", f"Found {nulls} null features.")
        )

    if "label_method" in available:
        if methods != {"verified_event_alignment"}:
            findings.append(
                Finding(
                    "ERROR",
                    "training.labels",
                    "Labels are not exclusively verified_event_alignment.",
                )
            )

    for target in TARGET_COLUMNS:
        if target not in available:
            continue
        counts = target_counts[target]
        severity = "ERROR" if target in PRODUCTION_TARGET_COLUMNS else "WARNING"
        if counts.get(0, 0) == 0 or counts.get(1, 0) == 0:
            findings.append(
                Finding(severity, f"training.{target}", "Both target classes are required.")
            )
        elif int(counts.get(1, 0)) < MIN_POSITIVE_SAMPLES:
            findings.append(
                Finding(
                    severity,
                    f"training.{target}",
                    f"Only {int(counts.get(1, 0))} positive samples.",
                )
            )

    return findings


def audit_models() -> list[Finding]:
    loader = PredictionLoader()
    findings = []
    for hazard, load, severity in (
        ("flood", loader.load_flood, "ERROR"),
        ("cyclone", loader.load_cyclone, "ERROR"),
        ("drought", loader.load_drought, "WARNING"),
    ):
        try:
            load()
        except Exception as error:
            findings.append(Finding(severity, f"models.{hazard}_contract", str(error)))
    return findings


def audit_sources() -> list[Finding]:
    findings = []
    era5 = list((PROJECT_ROOT / "data/silver/weather/era5").glob("year=*/*.parquet"))
    gpm = list((PROJECT_ROOT / "data/silver/weather/gpm").glob("year=*/gpm_*.parquet"))
    import pyarrow.parquet as pq

    required_era5 = {
        "soil_moisture_surface", "soil_moisture_root_zone", "runoff",
        "potential_evaporation",
    }
    valid_era5 = sum(
        required_era5.issubset(set(pq.ParquetFile(path).schema.names))
        for path in era5
    )
    if valid_era5 < 240:
        findings.append(
            Finding(
                "ERROR", "sources.era5",
                f"Found {valid_era5}/240 complete monthly partitions ({len(era5)} total).",
            )
        )
    if len(gpm) < GPM_EXPECTED_DAYS:
        findings.append(
            Finding(
                "ERROR",
                "sources.gpm",
                f"Found {len(gpm)}/{GPM_EXPECTED_DAYS} available daily partitions.",
            )
        )
    ground_truth = PROJECT_ROOT / "data/gold/ground_truth.parquet"
    if not ground_truth.exists():
        findings.append(Finding("ERROR", "ground_truth.exists", "Canonical ground truth is missing."))
    else:
        events = pd.read_parquet(
            ground_truth, columns=["hazard_type", "source", "source_event_id"]
        )
        counts = events["hazard_type"].value_counts().to_dict() if not events.empty else {}
        production_hazards = {"FLOOD", "CYCLONE"}
        for hazard in ("FLOOD", "DROUGHT", "CYCLONE"):
            if int(counts.get(hazard, 0)) < MIN_POSITIVE_SAMPLES:
                findings.append(
                    Finding(
                        "ERROR" if hazard in production_hazards else "WARNING",
                        f"ground_truth.{hazard.lower()}",
                        f"Found {int(counts.get(hazard, 0))}/{MIN_POSITIVE_SAMPLES} verified events.",
                    )
                )
            hazard_events = events.loc[events["hazard_type"].eq(hazard)].copy()
            hazard_events["source_event_id"] = (
                hazard_events["source_event_id"].fillna("").astype(str).str.strip()
            )
            independent = hazard_events.loc[
                hazard_events["source_event_id"].ne(""), ["source", "source_event_id"]
            ].drop_duplicates()
            if len(independent) < MIN_INDEPENDENT_EVENTS:
                findings.append(
                    Finding(
                        "WARNING",
                        f"ground_truth.{hazard.lower()}_diversity",
                        f"Found {len(independent)}/{MIN_INDEPENDENT_EVENTS} independent source events.",
                    )
                )
    return findings


def run(training_path: Path = TRAINING_DATASET) -> dict:
    findings = [*audit_sources(), *audit_training(training_path), *audit_models()]
    return {
        "ready": not any(item.severity == "ERROR" for item in findings),
        "findings": [asdict(item) for item in findings],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit SusBiome production artifacts.")
    parser.add_argument("--training-path", type=Path, default=TRAINING_DATASET)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    report = run(arguments.training_path)
    if arguments.json:
        print(json.dumps(report, indent=2))
    else:
        print("READY" if report["ready"] else "NOT READY")
        for finding in report["findings"]:
            print(f"[{finding['severity']}] {finding['check']}: {finding['message']}")
    raise SystemExit(0 if report["ready"] else 1)


if __name__ == "__main__":
    main()
