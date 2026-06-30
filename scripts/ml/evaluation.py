"""Shared, imbalance-aware evaluation for disaster classifiers."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


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
