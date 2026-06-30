"""
============================================================
SusBiome Dataset Merge
============================================================

Merge aligned provider datasets into one unified
DataFrame.

============================================================
"""

from __future__ import annotations

import pandas as pd


class DatasetMerger:
    """
    Merge aligned provider datasets.
    """

    # ======================================================
    # MERGE
    # ======================================================

    @staticmethod
    def merge(
        left: pd.DataFrame,
        right: pd.DataFrame,
        *,
        how: str = "inner",
    ) -> pd.DataFrame:
        """
        Merge two aligned datasets.
        """

        dataframe = pd.merge(

            left,

            right,

            how=how,

            on=[

                "longitude",

                "latitude",

                "valid_time",

            ],

        )

        if dataframe.empty:
            raise ValueError(
                "Provider datasets have no overlapping grid cells and dates."
            )
        return dataframe

    # ======================================================
    # REMOVE DUPLICATES
    # ======================================================

    @staticmethod
    def remove_duplicates(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Remove duplicate observations.
        """

        return dataframe.drop_duplicates(

            subset=[

                "longitude",

                "latitude",

                "valid_time",

            ]

        )

    # ======================================================
    # SORT
    # ======================================================

    @staticmethod
    def sort(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Sort observations.
        """

        return dataframe.sort_values(

            [

                "valid_time",

                "latitude",

                "longitude",

            ]

        ).reset_index(

            drop=True

        )

    # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
        *,
        left: pd.DataFrame,
        right: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Complete merge pipeline.
        """

        dataframe = self.merge(

            left,

            right,

        )

        dataframe = self.remove_duplicates(

            dataframe

        )

        dataframe = self.sort(

            dataframe

        )

        observation_columns = [
            column
            for column in dataframe.columns
            if column not in {"longitude", "latitude", "valid_time"}
        ]
        missing = int(dataframe[observation_columns].isna().sum().sum())
        if missing:
            raise ValueError(f"Fused observations contain {missing} missing values.")

        return dataframe
