"""Run post-collection SusBiome production stages in a repeatable order."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from ground_truth.build import DEFAULT_INPUTS, run as build_ground_truth
from scripts.features.hazards import build_year
from scripts.fusion.historical import fuse_year
from scripts.ingestion.historical_weather import GPM_EXPECTED_DAYS, status as ingestion_status
from scripts.labels.verified import run as align_verified_events
from scripts.labels.forecast_targets import build as build_forecast_targets
from scripts.ml.registry import ModelRegistry
from scripts.ml.trainer import MLTrainer
from scripts.operations.refresh import refresh as refresh_operational
from scripts.quality.audit import audit_sources, audit_training, run as audit_artifacts
from scripts.sources.common.config import PROJECT_ROOT

STATE_FILE = PROJECT_ROOT / "data/logs/production_pipeline.json"


def save_state(stage: str, payload: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(
            {"updated_at": datetime.now(UTC).isoformat(), "stage": stage, **payload},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


def prepare(events: Path, start_year: int, end_year: int, *, force: bool = False) -> dict:
    fused = []
    for year in range(start_year, end_year + 1):
        path = PROJECT_ROOT / f"data/fusion/historical/year={year:04d}/weather.parquet"
        fused.append(str(fuse_year(year) if force or not path.exists() else path))
    alignment = align_verified_events(events, start_year=start_year, end_year=end_year)
    features = []
    for year in range(start_year, end_year + 1):
        path = PROJECT_ROOT / f"data/gold/features_historical/year={year:04d}/features.parquet"
        features.append(str(build_year(year) if force or not path.exists() else path))
    forecast_targets = asdict(build_forecast_targets())
    result = {
        "fused": fused,
        "alignment": asdict(alignment),
        "features": features,
        "forecast_targets": forecast_targets,
    }
    save_state("prepared", result)
    return result


def train() -> dict:
    results = MLTrainer().train()
    save_state("trained", {"metrics": results})
    return results


def collection_complete() -> tuple[bool, dict]:
    status = ingestion_status()
    complete = (
        status["era5_valid_months"] >= 240
        and status["gpm_days"] >= GPM_EXPECTED_DAYS
    )
    return complete, status


def finalize(start_year: int, end_year: int, *, force: bool = False) -> dict:
    complete, sources = collection_complete()
    if not complete:
        result = {
            "status": "blocked",
            "reason": "Historical weather collection is incomplete.",
            "collection": sources,
        }
        save_state("blocked_collection", result)
        return result

    ground_truth = build_ground_truth(DEFAULT_INPUTS)
    save_state("ground_truth_built", ground_truth)
    prepared = prepare(
        PROJECT_ROOT / "data/gold/ground_truth.parquet",
        start_year,
        end_year,
        force=force,
    )
    preflight_findings = [
        *audit_sources(),
        *audit_training(PROJECT_ROOT / "data/gold/features_historical"),
    ]
    blocking = [finding for finding in preflight_findings if finding.severity == "ERROR"]
    if blocking:
        result = {
            "status": "blocked",
            "reason": "Pre-training audit failed.",
            "findings": [asdict(finding) for finding in preflight_findings],
        }
        save_state("blocked_preflight", result)
        return result

    result = {
        "status": "blocked",
        "reason": (
            "Leakage-safe horizon targets are prepared, but no horizon model has yet "
            "passed independent-event validation and the serving contract. The legacy "
            "same-window trainer is research-only."
        ),
        "prepared": prepared,
    }
    save_state("blocked_horizon_model", result)
    return result


def pipeline_status() -> dict:
    state = (
        json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if STATE_FILE.exists()
        else None
    )
    return {
        "collection": ingestion_status(),
        "pipeline": state,
        "models": ModelRegistry().state(),
        "audit": audit_artifacts(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--events", type=Path, required=True)
    prepare_parser.add_argument("--start-year", type=int, default=2006)
    prepare_parser.add_argument("--end-year", type=int, default=2025)
    prepare_parser.add_argument("--force", action="store_true")
    subparsers.add_parser("train")
    subparsers.add_parser("audit")
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--start-year", type=int, default=2006)
    finalize_parser.add_argument("--end-year", type=int, default=2025)
    finalize_parser.add_argument("--force", action="store_true")
    subparsers.add_parser("status")
    subparsers.add_parser("rollback")
    operational_parser = subparsers.add_parser("operational")
    operational_parser.add_argument("--skip-gpm", action="store_true")
    arguments = parser.parse_args()
    if arguments.command == "prepare":
        result = prepare(
            arguments.events,
            arguments.start_year,
            arguments.end_year,
            force=arguments.force,
        )
    elif arguments.command == "train":
        result = train()
    elif arguments.command == "audit":
        result = audit_artifacts()
    elif arguments.command == "finalize":
        result = finalize(arguments.start_year, arguments.end_year, force=arguments.force)
    elif arguments.command == "status":
        result = pipeline_status()
    elif arguments.command == "operational":
        result = refresh_operational(skip_gpm=arguments.skip_gpm)
    else:
        result = ModelRegistry().rollback()
    print(json.dumps(result, indent=2, default=str))
    if arguments.command == "audit" and not result["ready"]:
        raise SystemExit(1)
    if arguments.command == "finalize" and result["status"] != "complete":
        raise SystemExit(2)
    if arguments.command == "operational" and result["status"] != "complete":
        raise SystemExit(3)


if __name__ == "__main__":
    main()
