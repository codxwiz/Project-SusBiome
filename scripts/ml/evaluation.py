"""Shared, imbalance-aware evaluation for disaster classifiers."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

PRODUCTION_MINIMUMS = {
    "balanced_accuracy": 0.65,
    "precision": 0.10,
    "recall": 0.50,
    "pr_auc": 0.05,
    "true_positive": 10,
}


def model_quality_findings(hazard: str, metrics: dict) -> list[str]:
    """Return production-blocking metric failures for a hazard model."""
    if hazard not in {"flood", "cyclone"}:
        return []
    findings = []
    for metric, minimum in PRODUCTION_MINIMUMS.items():
        value = metrics.get(metric)
        if value is None or float(value) < minimum:
            findings.append(f"{hazard}.{metric}={value}; require >= {minimum}")
    return findings


def release_quality(metrics: dict) -> dict:
    findings = [
        finding
        for hazard in ("flood", "cyclone")
        for finding in model_quality_findings(hazard, metrics.get(hazard, {}))
    ]
    return {
        "passed": not findings,
        "minimums": PRODUCTION_MINIMUMS,
        "findings": findings,
    }


def positive_probability(model, features) -> np.ndarray:
    classes = list(getattr(model, "classes_", []))
    if 1 not in classes:
        return np.zeros(len(features), dtype=float)
    return model.predict_proba(features)[:, classes.index(1)]


def select_threshold(model, features, target) -> float:
    probabilities = positive_probability(model, features)
    if len(set(target)) < 2:
        return 0.5
    candidates = np.linspace(0.10, 0.90, 81)
    scores = [f1_score(target, probabilities >= threshold, zero_division=0) for threshold in candidates]
    return float(candidates[int(np.argmax(scores))])


def select_operating_threshold(
    model,
    features,
    target,
    *,
    minimum_precision: float = 0.10,
    minimum_recall: float = 0.50,
) -> float:
    """Select an F2-oriented threshold while enforcing release constraints when possible."""
    probabilities = positive_probability(model, features)
    if len(set(target)) < 2:
        return 0.5
    candidates = np.unique(
        np.concatenate(
            ([0.001], np.linspace(0.005, 0.5, 100), np.quantile(probabilities, np.linspace(0, 1, 101)))
        )
    )
    scored = []
    for threshold in candidates:
        prediction = probabilities >= threshold
        precision = precision_score(target, prediction, zero_division=0)
        recall = recall_score(target, prediction, zero_division=0)
        denominator = 4 * precision + recall
        f2 = 0.0 if denominator == 0 else 5 * precision * recall / denominator
        scored.append((precision >= minimum_precision and recall >= minimum_recall, f2, recall, precision, threshold))
    feasible = [item for item in scored if item[0]]
    selected = max(feasible or scored, key=lambda item: (item[1], item[2], item[3]))
    return float(selected[-1])


def event_level_metrics(
    probabilities: np.ndarray,
    target: pd.Series,
    groups: pd.Series,
    dates: pd.Series,
    *,
    threshold: float,
) -> dict:
    """Measure independent-event detection and false-alarm days."""
    frame = pd.DataFrame(
        {
            "probability": probabilities,
            "target": target.to_numpy(),
            "event_group": groups.fillna("").astype(str).to_numpy(),
            "date": pd.to_datetime(dates, utc=True).dt.normalize().to_numpy(),
        }
    )
    positive = frame.loc[frame["target"].eq(1) & frame["event_group"].ne("")]
    group_scores = positive.groupby("event_group")["probability"].max()
    detected = int(group_scores.ge(threshold).sum())
    negative = frame.loc[frame["target"].eq(0)].copy()
    false_alarm_days = int(
        negative.assign(alert=negative["probability"].ge(threshold))
        .groupby("date")["alert"]
        .any()
        .sum()
    )
    negative_days = int(negative["date"].nunique())
    return {
        "independent_events": int(len(group_scores)),
        "detected_events": detected,
        "event_recall": float(detected / len(group_scores)) if len(group_scores) else 0.0,
        "false_alarm_days": false_alarm_days,
        "negative_days": negative_days,
        "false_alarm_day_rate": float(false_alarm_days / negative_days) if negative_days else 0.0,
    }


def event_ranking_metrics(
    probabilities: np.ndarray,
    target: pd.Series,
    groups: pd.Series,
    dates: pd.Series,
) -> dict:
    """Measure where verified events rank among all grid cells on the same date."""
    frame = pd.DataFrame(
        {
            "probability": probabilities,
            "target": target.to_numpy(),
            "event_group": groups.fillna("").astype(str).to_numpy(),
            "date": pd.to_datetime(dates, utc=True).dt.normalize().to_numpy(),
        }
    )
    frame["daily_rank_fraction"] = frame.groupby("date")["probability"].rank(
        method="min", ascending=False, pct=True
    )
    positive = frame.loc[frame["target"].eq(1) & frame["event_group"].ne("")]
    event_ranks = positive.groupby("event_group")["daily_rank_fraction"].min()
    result = {
        "independent_events": int(len(event_ranks)),
        "median_best_daily_rank_fraction": (
            float(event_ranks.median()) if len(event_ranks) else None
        ),
    }
    for budget in (0.001, 0.005, 0.01, 0.05):
        detected = int(event_ranks.le(budget).sum())
        key = f"top_{budget:g}_fraction"
        result[key] = {
            "detected_events": detected,
            "event_recall": float(detected / len(event_ranks)) if len(event_ranks) else 0.0,
        }
    return result


def alert_budget_threshold(probabilities: np.ndarray, budget: float) -> float:
    """Choose a score threshold that alerts on at most a fraction of validation rows."""
    if not 0 < budget < 1:
        raise ValueError("Alert budget must be between zero and one.")
    return float(np.quantile(probabilities, 1.0 - budget, method="higher"))


def alert_burden_metrics(
    probabilities: np.ndarray,
    target: pd.Series,
    groups: pd.Series,
    dates: pd.Series,
    *,
    threshold: float,
) -> dict:
    """Report independent-event recall and the operational volume of alerts."""
    normalized_dates = pd.to_datetime(dates, utc=True).dt.normalize()
    alerts = probabilities >= threshold
    daily_alerts = pd.Series(alerts.astype("int8")).groupby(normalized_dates.to_numpy()).sum()
    event_metrics = event_level_metrics(
        probabilities, target, groups, dates, threshold=threshold
    )
    return {
        "threshold": float(threshold),
        "alerted_rows": int(alerts.sum()),
        "alerted_row_fraction": float(alerts.mean()),
        "mean_alerts_per_day": float(daily_alerts.mean()) if len(daily_alerts) else 0.0,
        "maximum_alerts_per_day": int(daily_alerts.max()) if len(daily_alerts) else 0,
        **event_metrics,
    }


def probability_diagnostics(
    probabilities: np.ndarray,
    target: pd.Series,
    *,
    bins: int = 10,
    calibrated: bool = False,
) -> dict:
    """Measure probability calibration without implying release eligibility."""
    values = np.asarray(probabilities, dtype=float)
    truth = np.asarray(target, dtype=int)
    if len(values) != len(truth) or not len(values):
        raise ValueError("Probability diagnostics require aligned non-empty inputs.")
    # Equal-width bins collapse rare-event probabilities into a single bucket.
    # Quantile bins retain useful reliability information at sub-1% prevalence.
    edges = np.unique(np.quantile(values, np.linspace(0.0, 1.0, bins + 1)))
    assignments = (
        np.zeros(len(values), dtype=int)
        if len(edges) < 3
        else np.clip(np.digitize(values, edges[1:-1], right=False), 0, len(edges) - 2)
    )
    calibration_error = 0.0
    populated_bins = 0
    for index in np.unique(assignments):
        selected = assignments == index
        if not selected.any():
            continue
        populated_bins += 1
        calibration_error += float(selected.mean()) * abs(
            float(values[selected].mean()) - float(truth[selected].mean())
        )
    brier = float(brier_score_loss(truth, values))
    climatology_brier = float(np.mean((truth - truth.mean()) ** 2))
    return {
        "rows": len(values),
        "positive_prevalence": float(truth.mean()),
        "mean_score": float(values.mean()),
        "brier_score": brier,
        "climatology_brier_score": climatology_brier,
        "brier_skill_score": (
            0.0 if climatology_brier == 0 else float(1.0 - brier / climatology_brier)
        ),
        "expected_calibration_error": float(calibration_error),
        "populated_bins": populated_bins,
        "calibrated_probability": calibrated,
    }


def evaluate_classifier(model, features, target, *, threshold: float = 0.5) -> dict:
    probability = positive_probability(model, features)
    prediction = (probability >= threshold).astype("int8")
    tn, fp, fn, tp = confusion_matrix(target, prediction, labels=[0, 1]).ravel()
    report = {
        "threshold": threshold,
        "accuracy": float(accuracy_score(target, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(target, prediction)),
        "precision": float(precision_score(target, prediction, zero_division=0)),
        "recall": float(recall_score(target, prediction, zero_division=0)),
        "f1": float(f1_score(target, prediction, zero_division=0)),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }
    if len(set(target)) == 2:
        report["roc_auc"] = float(roc_auc_score(target, probability))
        report["pr_auc"] = float(average_precision_score(target, probability))
    else:
        report["roc_auc"] = None
        report["pr_auc"] = None
    return report
