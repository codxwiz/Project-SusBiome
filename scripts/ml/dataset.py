"""
============================================================
Machine Learning Dataset
============================================================

Loads and prepares datasets for Machine Learning.

Pipeline

Feature Dataset
        ↓
Validation
        ↓
Feature Selection
        ↓
Dataset Split

============================================================
"""

from __future__ import annotations

import logging

from pathlib import Path

import pandas as pd

from scripts.ml.models import (
    DROP_COLUMNS,
    EXCLUDED_COLUMNS,
    RANDOM_STATE,
    TARGET_COLUMNS,
    FEATURE_COLUMNS,
    MIN_HISTORY_DAYS,
    MIN_POSITIVE_SAMPLES,
    MAX_NEGATIVE_RATIO,
    MIN_NEGATIVES_PER_PARTITION,
    TRAIN_SIZE,
    VALIDATION_SIZE,
    TEST_SIZE,
)
from scripts.fusion.models import NORTHEAST_INDIA_BOUNDS

logger = logging.getLogger(
    "susbiome.ml.dataset"
)


# ==========================================================
# MACHINE LEARNING DATASET
# ==========================================================

class MLDataset:
    """
    Prepare datasets for model training.
    """

    # ======================================================
    # LOAD
    # ======================================================

    @staticmethod
    def load(
        path: Path,
        *,
        target: str | None = None,
    ) -> pd.DataFrame:

        logger.info(
            "Loading %s",
            path,
        )

        if path.is_file():
            return pd.read_parquet(path)
        if not path.is_dir():
            raise FileNotFoundError(path)
        files = sorted(path.glob("year=*/features.parquet"))
        if not files:
            raise FileNotFoundError(f"No feature partitions under {path}")
        frames = []
        for index, partition in enumerate(files):
            frame = pd.read_parquet(partition)
            if target is not None and target in frame:
                positive = frame[frame[target] == 1]
                negative = frame[frame[target] == 0]
                negative_limit = max(
                    MIN_NEGATIVES_PER_PARTITION,
                    len(positive) * MAX_NEGATIVE_RATIO,
                )
                if len(negative) > negative_limit:
                    negative = negative.sample(
                        n=negative_limit,
                        random_state=RANDOM_STATE + index,
                    )
                frame = pd.concat([positive, negative], ignore_index=True)
            frames.append(frame)
        return pd.concat(frames, ignore_index=True)

    # ======================================================
    # VALIDATE
    # ======================================================

    @staticmethod
    def validate(
        dataframe: pd.DataFrame,
        *,
        target: str,
    ) -> None:

        if dataframe.empty:

            raise ValueError(
                "Dataset is empty."
            )

        if target not in dataframe.columns:

            raise ValueError(
                f"Missing target column: {target}"
            )

        missing = [column for column in FEATURE_COLUMNS if column not in dataframe]
        if missing:
            raise ValueError("Missing feature columns: " + ", ".join(missing))

    # ======================================================
    # FEATURES
    # ======================================================

    @staticmethod
    def features(
        dataframe: pd.DataFrame,
        *,
        target: str,
    ) -> pd.DataFrame:

        #
        # Remove metadata
        #

        return dataframe.loc[:, FEATURE_COLUMNS].copy()

    @staticmethod
    def validate_training_quality(dataframe: pd.DataFrame, *, target: str) -> None:
        """Reject datasets that can produce plausible-looking invalid models."""
        timestamps = pd.to_datetime(dataframe["valid_time"], utc=True, errors="coerce")
        history_days = timestamps.dt.normalize().nunique()
        if history_days < MIN_HISTORY_DAYS:
            raise ValueError(
                f"Training requires at least {MIN_HISTORY_DAYS} distinct days; "
                f"found {history_days}."
            )

        counts = dataframe[target].value_counts(dropna=False)
        if 0 not in counts or 1 not in counts:
            raise ValueError(f"Target {target} must contain both classes 0 and 1.")
        if int(counts.get(1, 0)) < MIN_POSITIVE_SAMPLES:
            raise ValueError(
                f"Target {target} requires at least {MIN_POSITIVE_SAMPLES} "
                f"positive samples; found {int(counts.get(1, 0))}."
            )

        missing_values = int(dataframe[FEATURE_COLUMNS].isna().sum().sum())
        if missing_values:
            raise ValueError(
                f"Training features contain {missing_values} missing values."
            )

        if "label_method" not in dataframe.columns:
            raise ValueError(
                "Training data is missing label_method provenance."
            )
        invalid_methods = set(dataframe["label_method"].dropna().unique()) - {
            "verified_event_alignment"
        }
        if invalid_methods:
            raise ValueError(
                "Production training requires verified event labels; found: "
                + ", ".join(sorted(map(str, invalid_methods)))
            )

        bounds = NORTHEAST_INDIA_BOUNDS
        outside = ~(
            dataframe["latitude"].between(
                bounds["min_latitude"], bounds["max_latitude"]
            )
            & dataframe["longitude"].between(
                bounds["min_longitude"], bounds["max_longitude"]
            )
        )
        if outside.any():
            raise ValueError(
                f"Training contains {int(outside.sum())} rows outside Northeast India."
            )

    # ======================================================
    # TARGET
    # ======================================================

    @staticmethod
    def target(
        dataframe: pd.DataFrame,
        *,
        target: str,
    ) -> pd.Series:

        return dataframe[target]

    # ======================================================
    # SPLIT
    # ======================================================

    @staticmethod
    def split(
        X: pd.DataFrame,
        y: pd.Series,
        timestamps: pd.Series | None = None,
        groups: pd.Series | None = None,
    ):

        if timestamps is None:
            train_end = int(len(X) * TRAIN_SIZE)
            valid_end = train_end + int(len(X) * VALIDATION_SIZE)
            train_mask = pd.Series(False, index=X.index)
            valid_mask = train_mask.copy()
            test_mask = train_mask.copy()
            train_mask.iloc[:train_end] = True
            valid_mask.iloc[train_end:valid_end] = True
            test_mask.iloc[valid_end:] = True
        elif groups is None:
            dates = pd.to_datetime(timestamps, utc=True).dt.normalize()
            unique_dates = sorted(dates.unique())
            train_date_count = max(1, int(len(unique_dates) * TRAIN_SIZE))
            valid_date_count = max(1, int(len(unique_dates) * VALIDATION_SIZE))
            train_dates = set(unique_dates[:train_date_count])
            valid_dates = set(
                unique_dates[train_date_count : train_date_count + valid_date_count]
            )
            train_mask = dates.isin(train_dates)
            valid_mask = dates.isin(valid_dates)
            test_mask = ~(train_mask | valid_mask)
        else:
            dates = pd.to_datetime(timestamps, utc=True).dt.normalize()
            normalized_groups = groups.fillna("").astype(str).str.strip()
            unique_dates = sorted(dates.unique())
            parent = {date: date for date in unique_dates}

            def find(value):
                while parent[value] != value:
                    parent[value] = parent[parent[value]]
                    value = parent[value]
                return value

            def union(left, right):
                left_root, right_root = find(left), find(right)
                if left_root != right_root:
                    parent[right_root] = left_root

            grouped = pd.DataFrame({"date": dates, "group": normalized_groups})
            for _, values in grouped.loc[grouped["group"].ne("")].groupby("group"):
                group_dates = sorted(values["date"].unique())
                for date in group_dates[1:]:
                    union(group_dates[0], date)

            components: dict[object, list] = {}
            for date in unique_dates:
                components.setdefault(find(date), []).append(date)
            ordered = sorted(components.values(), key=lambda values: min(values))
            if len(ordered) < 3:
                raise ValueError("Event-group split requires at least three temporal groups.")

            total_dates = len(unique_dates)
            train_target = max(1, int(total_dates * TRAIN_SIZE))
            valid_target = max(1, int(total_dates * VALIDATION_SIZE))
            train_dates: set = set()
            valid_dates: set = set()
            test_dates: set = set()
            for component in ordered:
                destination = (
                    train_dates
                    if len(train_dates) < train_target
                    else valid_dates
                    if len(valid_dates) < valid_target
                    else test_dates
                )
                destination.update(component)
            train_mask = dates.isin(train_dates)
            valid_mask = dates.isin(valid_dates)
            test_mask = dates.isin(test_dates)

        if not train_mask.any() or not valid_mask.any() or not test_mask.any():
            raise ValueError("Temporal split produced an empty dataset partition.")

        X_train, y_train = X.loc[train_mask], y.loc[train_mask]
        X_valid, y_valid = X.loc[valid_mask], y.loc[valid_mask]
        X_test, y_test = X.loc[test_mask], y.loc[test_mask]

        return (

            X_train,

            X_valid,

            X_test,

            y_train,

            y_valid,

            y_test,

        )

    # ======================================================
    # BUILD
    # ======================================================

    @classmethod
    def build(
        cls,
        *,
        path: Path,
        target: str,
    ):

        dataframe = cls.load(path, target=target)

        cls.validate(

            dataframe,

            target=target,

        )

        cls.validate_training_quality(dataframe, target=target)

        dataframe = dataframe.sort_values(
            ["valid_time", "latitude", "longitude"]
        ).reset_index(drop=True)

        X = cls.features(

            dataframe,

            target=target,

        )

        y = cls.target(

            dataframe,

            target=target,

        )

        logger.info(
            "Dataset prepared."
        )

        group_column = target.replace("_risk", "_event_group")
        groups = dataframe[group_column] if group_column in dataframe else None
        return cls.split(

            X,

            y,

            dataframe["valid_time"],

            groups,

        )
