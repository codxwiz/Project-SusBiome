"""
============================================================
SusBiome Data Alignment
============================================================

Standardizes provider datasets before fusion.

Responsibilities
----------------
- Load Parquet
- Normalize coordinates
- Normalize timestamps
- Standardize column names

============================================================
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.fusion.models import NORTHEAST_INDIA_BOUNDS


class DataAligner:
    """
    Align provider datasets into a common schema.
    """

    # ======================================================
    # LOAD
    # ======================================================

    @staticmethod
    def load(
        path: Path,
    ) -> pd.DataFrame:

        return pd.read_parquet(
            path
        )

    # ======================================================
    # COORDINATES
    # ======================================================

    @staticmethod
    def align_coordinates(
        dataframe: pd.DataFrame,
        decimals: int = 4,
    ) -> pd.DataFrame:
        """
        Round coordinates to a common precision.
        """

        dataframe = dataframe.copy()

        dataframe["longitude"] = (
            (pd.to_numeric(dataframe["longitude"]) + 180) % 360
        ) - 180
        dataframe["latitude"] = pd.to_numeric(dataframe["latitude"])

        dataframe["latitude"] = (

            dataframe["latitude"]

            .round(decimals)

        )

        dataframe["longitude"] = (

            dataframe["longitude"]

            .round(decimals)

        )

        return dataframe

    @staticmethod
    def filter_region(
        dataframe: pd.DataFrame,
        bounds: dict[str, float] = NORTHEAST_INDIA_BOUNDS,
    ) -> pd.DataFrame:
        """Limit observations to the platform's supported geography."""
        mask = (
            dataframe["latitude"].between(
                bounds["min_latitude"], bounds["max_latitude"]
            )
            & dataframe["longitude"].between(
                bounds["min_longitude"], bounds["max_longitude"]
            )
        )
        return dataframe.loc[mask].copy()
    
    @staticmethod
    def align_grid(
        dataframe: pd.DataFrame,
        *,
        resolution: float = 0.25,
    ) -> pd.DataFrame:
        """
        Snap coordinates to the SusBiome analysis grid.
        """

        dataframe = dataframe.copy()

        dataframe["longitude"] = (
            dataframe["longitude"] / resolution
        ).round() * resolution

        dataframe["latitude"] = (
            dataframe["latitude"] / resolution
        ).round() * resolution

        return dataframe

    # ======================================================
    # TIME
    # ======================================================

    @staticmethod
    def align_time(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Ensure valid_time is UTC datetime.
        """

        dataframe = dataframe.copy()

        if "valid_time" in dataframe.columns:

            dataframe["valid_time"] = (

                pd.to_datetime(

                    dataframe["valid_time"],

                    utc=True,

                )

                .dt.normalize()

        )

        return dataframe

    # ======================================================
    # VARIABLE
    # ======================================================

    def standardize(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:

        dataframe = self.align(dataframe)

        if "value" in dataframe.columns:
            dataframe = dataframe.rename(
                columns={
                    "value": "temperature",
                }
            )

        return dataframe

    # ======================================================
    # ALIGN
    # ======================================================

    def align(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Complete alignment pipeline.
        """

        dataframe = self.align_coordinates(
            dataframe
        )

        dataframe = self.filter_region(dataframe)

        dataframe = self.align_grid(
            dataframe
        )

        dataframe = self.align_time(
            dataframe
        )

        dataframe = self.aggregate(
            dataframe
        )

        return dataframe

    @staticmethod
    def aggregate(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Aggregate observations that map to the same grid cell.
        """

        keys = [
            "longitude",
            "latitude",
        ]

        if "valid_time" in dataframe.columns:
            keys.append("valid_time")

        value_columns = [

            c

            for c in dataframe.columns

            if c not in keys

        ]

        if not value_columns:
            raise ValueError("Dataset contains no observation columns.")

        return (

            dataframe

            .groupby(

                keys,

                as_index=False,

            )[value_columns]

            .mean()

        )
