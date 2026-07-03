"""Train and backtest horizon-specific flood and cyclone model candidates."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier

from scripts.ml.dataset import MLDataset
from scripts.ml.evaluation import (
    alert_budget_threshold,
    alert_burden_metrics,
    evaluate_classifier,
    event_level_metrics,
    event_ranking_metrics,
    probability_diagnostics,
    positive_probability,
    select_operating_threshold,
)
from scripts.ml.models import FEATURE_COLUMNS, RANDOM_STATE
from scripts.sources.common.config import PROJECT_ROOT

DATASET = PROJECT_ROOT / "data/gold/forecast_targets"
OUTPUT_ROOT = PROJECT_ROOT / "models/experiments/horizons"
REPORT_PATH = PROJECT_ROOT / "data/quality/horizon_experiment.json"
BACKTEST_PATH = PROJECT_ROOT / "data/quality/horizon_backtest.json"
TARGETS = tuple(
    f"{hazard}_risk_{horizon}d"
    for hazard in ("flood", "cyclone")
    for horizon in (3, 7, 14)
)
HORIZON_FEATURES = ["latitude", "longitude", *FEATURE_COLUMNS]
ALERT_BUDGETS = (0.001, 0.005, 0.01)


def candidate_models() -> dict[str, object]:
    return {
        "random_forest": RandomForestClassifier(
            n_estimators=350,
            max_depth=16,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            max_samples=0.85,
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=350,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            learning_rate=0.06,
            max_iter=250,
            max_leaf_nodes=31,
            min_samples_leaf=20,
            l2_regularization=1.0,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
    }


def load_full_period(target: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    group_column = target.replace("_risk", "_event_group")
    columns = [*HORIZON_FEATURES, target, group_column, "valid_time"]
    frames = []
    for path in sorted(DATASET.glob("year=*/features.parquet")):
        year = int(path.parent.name.split("=", 1)[1])
        if start.year <= year <= end.year:
            frame = pd.read_parquet(path, columns=columns)
            times = pd.to_datetime(frame["valid_time"], utc=True)
            frames.append(frame.loc[times.between(start, end)])
    if not frames:
        raise ValueError("No full evaluation partitions were selected.")
    return pd.concat(frames, ignore_index=True)


def evaluation_periods(target: str) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    sampled = MLDataset.load(DATASET, target=target).sort_values(
        ["valid_time", "latitude", "longitude"]
    ).reset_index(drop=True)
    group_column = target.replace("_risk", "_event_group")
    split = MLDataset.split(
        sampled[HORIZON_FEATURES],
        sampled[target],
        sampled["valid_time"],
        sampled[group_column],
    )
    _, x_valid, x_test, _, _, _ = split
    times = pd.to_datetime(sampled["valid_time"], utc=True)
    return (
        times.loc[x_valid.index].min().normalize(),
        times.loc[x_valid.index].max().normalize(),
        times.loc[x_test.index].min().normalize(),
        times.loc[x_test.index].max().normalize(),
    )


def operational_backtest(
    model,
    target: str,
    full_validation: pd.DataFrame,
    full_test: pd.DataFrame,
) -> dict:
    group_column = target.replace("_risk", "_event_group")
    validation_probabilities = positive_probability(model, full_validation[HORIZON_FEATURES])
    probabilities = positive_probability(model, full_test[HORIZON_FEATURES])
    alert_budgets = {}
    for budget in ALERT_BUDGETS:
        threshold = alert_budget_threshold(validation_probabilities, budget)
        alert_budgets[str(budget)] = alert_burden_metrics(
            probabilities,
            full_test[target],
            full_test[group_column],
            full_test["valid_time"],
            threshold=threshold,
        )
    return {
        "validation_score_summary": {
            "minimum": float(np.min(validation_probabilities)),
            "median": float(np.median(validation_probabilities)),
            "maximum": float(np.max(validation_probabilities)),
        },
        "test_score_summary": {
            "minimum": float(np.min(probabilities)),
            "median": float(np.median(probabilities)),
            "maximum": float(np.max(probabilities)),
        },
        "event_ranking_metrics": event_ranking_metrics(
            probabilities,
            full_test[target],
            full_test[group_column],
            full_test["valid_time"],
        ),
        "probability_diagnostics": probability_diagnostics(probabilities, full_test[target]),
        "alert_budget_metrics": alert_budgets,
    }


def run_target(target: str) -> dict:
    sampled = MLDataset.load(DATASET, target=target)
    MLDataset.validate(sampled, target=target)
    MLDataset.validate_training_quality(sampled, target=target)
    sampled = sampled.sort_values(["valid_time", "latitude", "longitude"]).reset_index(drop=True)
    x = sampled[HORIZON_FEATURES]
    y = sampled[target]
    group_column = target.replace("_risk", "_event_group")
    groups = sampled[group_column]
    split = MLDataset.split(x, y, sampled["valid_time"], groups)
    x_train, x_valid, x_test, y_train, y_valid, y_test = split
    validation_start = pd.to_datetime(
        sampled.loc[x_valid.index, "valid_time"], utc=True
    ).min().normalize()
    validation_end = pd.to_datetime(
        sampled.loc[x_valid.index, "valid_time"], utc=True
    ).max().normalize()
    test_start = pd.to_datetime(sampled.loc[x_test.index, "valid_time"], utc=True).min().normalize()
    test_end = pd.to_datetime(sampled.loc[x_test.index, "valid_time"], utc=True).max().normalize()
    full_validation = load_full_period(target, validation_start, validation_end)
    x_full_validation = full_validation[HORIZON_FEATURES]
    y_full_validation = full_validation[target]
    candidates = {}
    best = None
    best_score = (-1.0, -1.0)
    for name, model in candidate_models().items():
        model.fit(x_train, y_train)
        threshold = select_operating_threshold(model, x_full_validation, y_full_validation)
        validation = evaluate_classifier(
            model, x_full_validation, y_full_validation, threshold=threshold
        )
        candidates[name] = {"threshold": threshold, "validation": validation}
        score = (float(validation.get("pr_auc") or 0.0), float(validation["recall"]))
        if score > best_score:
            best_score = score
            best = (name, model, threshold)
    assert best is not None
    model_name, model, threshold = best

    full_test = load_full_period(target, test_start, test_end)
    x_full = full_test[HORIZON_FEATURES]
    y_full = full_test[target]
    probabilities = positive_probability(model, x_full)
    row_metrics = evaluate_classifier(model, x_full, y_full, threshold=threshold)
    event_metrics = event_level_metrics(
        probabilities,
        y_full,
        full_test[group_column],
        full_test["valid_time"],
        threshold=threshold,
    )
    operational = operational_backtest(model, target, full_validation, full_test)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    model.susbiome_threshold_ = threshold
    model.susbiome_metadata_ = {
        "schema_version": 2,
        "target": target,
        "feature_columns": HORIZON_FEATURES,
        "label_method": "verified_future_event_alignment",
        "trained_at": datetime.now(UTC).isoformat(),
        "candidate_model": model_name,
        "row_metrics": row_metrics,
        "event_metrics": event_metrics,
        **operational,
        "production_eligible": False,
        "probability_status": "research_uncalibrated",
    }
    joblib.dump(model, OUTPUT_ROOT / f"{target}.joblib")
    return {
        "target": target,
        "selected_model": model_name,
        "threshold": threshold,
        "sampled_rows": {
            "train": len(x_train), "validation": len(x_valid), "test": len(x_test),
        },
        "full_validation_rows": len(full_validation),
        "full_test_rows": len(full_test),
        "full_validation_period": {
            "start": str(validation_start.date()), "end": str(validation_end.date())
        },
        "full_test_period": {"start": str(test_start.date()), "end": str(test_end.date())},
        "class_counts": {
            "train_positive": int(y_train.sum()),
            "validation_positive": int(y_full_validation.sum()),
            "full_test_positive": int(y_full.sum()),
        },
        "candidates": candidates,
        "row_metrics": row_metrics,
        "event_metrics": event_metrics,
        **operational,
        "artifact": str(OUTPUT_ROOT / f"{target}.joblib"),
    }


def run(targets: tuple[str, ...] = TARGETS) -> dict:
    invalid = set(targets) - set(TARGETS)
    if invalid:
        raise ValueError("Unsupported targets: " + ", ".join(sorted(invalid)))
    previous = {}
    if REPORT_PATH.exists():
        previous = json.loads(REPORT_PATH.read_text(encoding="utf-8")).get("targets", {})
    results = {target: run_target(target) for target in targets}
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "production_eligible": False,
        "targets": {**previous, **results},
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def backtest_existing(targets: tuple[str, ...]) -> dict:
    """Evaluate saved experimental artifacts without fitting models again."""
    results = {}
    for target in targets:
        artifact = OUTPUT_ROOT / f"{target}.joblib"
        if not artifact.exists():
            raise FileNotFoundError(f"No experimental artifact for {target}: {artifact}")
        validation_start, validation_end, test_start, test_end = evaluation_periods(target)
        full_validation = load_full_period(target, validation_start, validation_end)
        full_test = load_full_period(target, test_start, test_end)
        results[target] = {
            "full_validation_period": {
                "start": str(validation_start.date()),
                "end": str(validation_end.date()),
            },
            "full_test_period": {
                "start": str(test_start.date()),
                "end": str(test_end.date()),
            },
            "full_validation_rows": len(full_validation),
            "full_test_rows": len(full_test),
            **operational_backtest(
                joblib.load(artifact), target, full_validation, full_test
            ),
        }
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "production_eligible": False,
        "targets": results,
    }
    BACKTEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKTEST_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", action="append", choices=TARGETS)
    parser.add_argument("--backtest-only", action="store_true")
    arguments = parser.parse_args()
    targets = tuple(arguments.target) if arguments.target else TARGETS
    result = backtest_existing(targets) if arguments.backtest_only else run(targets)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
