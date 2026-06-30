"""Compare recent model inputs with the training reference distribution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.ml.models import FEATURE_COLUMNS


def population_stability_index(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    reference = pd.to_numeric(reference, errors="coerce").dropna()
    current = pd.to_numeric(current, errors="coerce").dropna()
    if reference.empty or current.empty:
        return float("inf")
    edges = np.unique(reference.quantile(np.linspace(0, 1, bins + 1)).to_numpy())
    if len(edges) < 3:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    expected = pd.cut(reference, edges, include_lowest=True).value_counts(normalize=True, sort=False)
    actual = pd.cut(current, edges, include_lowest=True).value_counts(normalize=True, sort=False)
    expected = expected.clip(lower=1e-6)
    actual = actual.clip(lower=1e-6)
    return float(((actual - expected) * np.log(actual / expected)).sum())


def drift_report(reference: pd.DataFrame, current: pd.DataFrame) -> dict:
    missing = [column for column in FEATURE_COLUMNS if column not in reference or column not in current]
    if missing:
        raise ValueError("Missing drift features: " + ", ".join(missing))
    scores = {
        column: population_stability_index(reference[column], current[column])
        for column in FEATURE_COLUMNS
    }
    return {
        "drift_detected": any(score >= 0.25 for score in scores.values()),
        "warning_features": sorted(column for column, score in scores.items() if score >= 0.10),
        "critical_features": sorted(column for column, score in scores.items() if score >= 0.25),
        "psi": scores,
    }


def load(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = drift_report(load(arguments.reference), load(arguments.current))
    rendered = json.dumps(report, indent=2)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    raise SystemExit(1 if report["drift_detected"] else 0)


if __name__ == "__main__":
    main()
