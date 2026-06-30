"""
============================================================
SusBiome Unified Dataset
============================================================

Load and save the unified SusBiome dataset.

Responsibilities
----------------
- Validate dataset
- Save Parquet
- Load Parquet

============================================================
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class UnifiedDataset:
    """
    Unified SusBiome dataset.
    """

    REQUIRED_COLUMNS = [

        "longitude",

        "latitude",

        "valid_time",

    ]

    # ======================================================
    # VALIDATE
    # ======================================================

    @classmethod
    def validate(
        cls,
        dataframe: pd.DataFrame,
    ) -> None:
        """
        Validate required columns.
        """

        missing = [

            column

            for column in cls.REQUIRED_COLUMNS

            if column not in dataframe.columns

        ]

        if missing:

            raise ValueError(

                "Missing columns: "

                + ", ".join(missing)

            )

    # ======================================================
    # SAVE
    # ======================================================

    @classmethod
    def save(
        cls,
        dataframe: pd.DataFrame,
        path: Path,
    ) -> Path:
        """
        Save unified dataset.
        """

        cls.validate(

            dataframe

        )

        path.parent.mkdir(

            parents=True,

            exist_ok=True,

        )

        dataframe.to_parquet(

            path,

            index=False,

            compression="zstd",

        )

        return path

    # ======================================================
    # LOAD
    # ======================================================

    @classmethod
    def load(
        cls,
        path: Path,
    ) -> pd.DataFrame:
        """
        Load unified dataset.
        """

        dataframe = pd.read_parquet(

            path

        )

        cls.validate(

            dataframe

        )

        return dataframe

    # ======================================================
    # INFO
    # ======================================================

    @staticmethod
    def info(
        dataframe: pd.DataFrame,
    ) -> None:
        """
        Print dataset information.
        """

        print()

        print("=" * 60)

        print("UNIFIED DATASET")

        print("=" * 60)

        print()

        print(

            f"Rows : {len(dataframe):,}"

        )

        print(

            f"Columns : "

            f"{list(dataframe.columns)}"

        )

        print()

        print(

            dataframe.head()

        )