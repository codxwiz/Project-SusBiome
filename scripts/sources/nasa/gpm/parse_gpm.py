"""
============================================================
NASA GPM Parser
============================================================

Purpose
-------
Convert NASA GPM IMERG NetCDF4 datasets into the
SusBiome Silver data format (Apache Parquet).

Pipeline

Bronze (.nc4)

    ↓

Read NetCDF4

    ↓

Validate dataset

    ↓

Extract variables

    ↓

Create DataFrame

    ↓

Write Parquet

This module performs no downloading and no feature
engineering. It is responsible only for transforming
raw satellite data into structured tabular data.

============================================================
"""
from __future__ import annotations

import logging

from pathlib import Path

import netCDF4 as nc
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
# ==========================================================
# LOGGER
# ==========================================================

logger = logging.getLogger(
    "susbiome.nasa.gpm.parser"
)

if not logger.handlers:

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    console = logging.StreamHandler()

    console.setFormatter(formatter)

    logger.addHandler(console)
    # ==========================================================
# GPM PARSER
# ==========================================================

class GPMParser:
    """
    Production parser for NASA GPM IMERG datasets.

    Input:
        NetCDF4 (.nc4)

    Output:
        Apache Parquet (.parquet)
    """
            # ======================================================
    # REQUIRED VARIABLES
    # ======================================================

    REQUIRED_VARIABLES = {

        "precipitation",

        "lon",

        "lat",

        "time",

    }

    # ======================================================
    # OPTIONAL VARIABLES
    # ======================================================

    OPTIONAL_VARIABLES = {

        "randomError",

        "probabilityLiquidPrecipitation",

        "MWprecipitation",

        "precipitation_cnt",

        "precipitation_cnt_cond",

        "MWprecipitation_cnt",

        "MWprecipitation_cnt_cond",

        "randomError_cnt",

    }

    # ======================================================
    # REQUIRED DIMENSIONS
    # ======================================================

    REQUIRED_DIMENSIONS = {

        "time",

        "lon",

        "lat",

    }
        # ======================================================
    # INITIALIZE
    # ======================================================

    def __init__(
        self,
        input_file: Path,
        output_file: Path,
    ) -> None:
        """
        Initialize the parser.

        Parameters
        ----------
        input_file
            Path to the Bronze NetCDF4 (.nc4) file.

        output_file
            Path where the Silver Parquet file will be written.
        """

        self.input_file = Path(input_file)

        self.output_file = Path(output_file)

        self.dataset: nc.Dataset | None = None
        self.metadata: dict[str, object] = {}

        self.coordinates: dict[str, np.ndarray] = {}

        self.precipitation: np.ndarray | None = None

        self.dataframe: pd.DataFrame | None = None
            # ======================================================
    # OPEN DATASET
    # ======================================================

    def open_dataset(
        self,
    ) -> None:
        """
        Open the NetCDF4 dataset.
        """

        logger.info(

            f"Opening {self.input_file}"

        )

        if not self.input_file.exists():

            raise FileNotFoundError(

                f"Input file not found: "

                f"{self.input_file}"

            )

        self.dataset = nc.Dataset(

            self.input_file,

            mode="r",

        )

        logger.info(

            "Dataset opened successfully."

        )
            # ======================================================
    # DATASET INFO
    # ======================================================

    def dataset_info(
        self,
    ) -> dict[str, object]:
        """
        Return basic information about the dataset.
        """

        if self.dataset is None:

            raise RuntimeError(

                "Dataset is not open."

            )

        return {

            "dimensions": list(

                self.dataset.dimensions.keys()

            ),

            "variables": list(

                self.dataset.variables.keys()

            ),

            "attributes": list(

                self.dataset.ncattrs()

            ),

        }
        # ======================================================
    # LOG DATASET INFO
    # ======================================================

    def log_dataset_info(
        self,
    ) -> None:
        """
        Log basic dataset metadata.
        """

        info = self.dataset_info()

        logger.info(

            f"Dimensions: "

            f"{len(info['dimensions'])}"

        )

        logger.info(

            f"Variables: "

            f"{len(info['variables'])}"

        )

        logger.info(

            f"Attributes: "

            f"{len(info['attributes'])}"

        )
            # ======================================================
    # VALIDATE
    # ======================================================

    def validate(
        self,
    ) -> None:
        """
        Validate the dataset structure.
        """

        if self.dataset is None:

            raise RuntimeError(

                "Dataset is not open."

            )

        #
        # Dimensions
        #
        dimensions = set(

            self.dataset.dimensions.keys()

        )

        missing = (

            self.REQUIRED_DIMENSIONS

            - dimensions

        )

        if missing:

            raise ValueError(

                "Missing dimensions: "

                + ", ".join(sorted(missing))

            )

        #
        # Variables
        #
        variables = set(

            self.dataset.variables.keys()

        )

        missing = (

            self.REQUIRED_VARIABLES

            - variables

        )

        if missing:

            raise ValueError(

                "Missing variables: "

                + ", ".join(sorted(missing))

            )

        logger.info(

            "Dataset validation passed."

        )
            # ======================================================
    # SUMMARY
    # ======================================================

    def summary(
        self,
    ) -> None:
        """
        Log dataset summary.
        """

        info = self.dataset_info()

        logger.info(

            f"Variables : "

            f"{len(info['variables'])}"

        )

        logger.info(

            f"Dimensions: "

            f"{len(info['dimensions'])}"

        )

        logger.info(

            f"Attributes: "

            f"{len(info['attributes'])}"

        )
            # ======================================================
    # INSPECT
    # ======================================================

    def inspect(
        self,
    ) -> None:
        """
        Print detailed information about the dataset.

        This method is intended for production verification
        of new NASA product versions.
        """

        if self.dataset is None:

            raise RuntimeError(
                "Dataset is not open."
            )

        logger.info("===== DIMENSIONS =====")

        for name, dimension in self.dataset.dimensions.items():

            logger.info(
                f"{name}: {len(dimension)}"
            )

        logger.info("===== VARIABLES =====")

        for name, variable in self.dataset.variables.items():

            logger.info(
                f"{name} | "
                f"dtype={variable.dtype} | "
                f"dimensions={variable.dimensions}"
            )

        logger.info("===== GLOBAL ATTRIBUTES =====")

        for attribute in self.dataset.ncattrs():

            logger.info(
                f"{attribute}: "
                f"{self.dataset.getncattr(attribute)}"
            )
                # ======================================================
    # EXTRACT METADATA
    # ======================================================

    def extract_metadata(
        self,
    ) -> None:
        """
        Extract global dataset metadata.
        """

        if self.dataset is None:

            raise RuntimeError(

                "Dataset is not open."

            )

        self.metadata = {

            "title": self.dataset.getncattr("title"),

            "doi": self.dataset.getncattr("DOI"),

            "begin_date": self.dataset.getncattr("BeginDate"),

            "begin_time": self.dataset.getncattr("BeginTime"),

            "end_date": self.dataset.getncattr("EndDate"),

            "end_time": self.dataset.getncattr("EndTime"),

            "production_time": self.dataset.getncattr(
                "ProductionTime"
            ),

        }

        logger.info(

            "Metadata extracted."

        )
            # ======================================================
    # METADATA SUMMARY
    # ======================================================

    def metadata_summary(
        self,
    ) -> None:
        """
        Log extracted metadata.
        """

        if not self.metadata:

            raise RuntimeError(

                "Metadata has not been extracted."

            )

        logger.info(

            f"Title: {self.metadata['title']}"

        )

        logger.info(

            f"Coverage: "

            f"{self.metadata['begin_date']} "

            f"{self.metadata['begin_time']} "

            f"→ "

            f"{self.metadata['end_date']} "

            f"{self.metadata['end_time']}"

        )

        logger.info(

            f"DOI: {self.metadata['doi']}"

        )

        logger.info(

            f"Production: "

            f"{self.metadata['production_time']}"

        )
            # ======================================================
    # EXTRACT COORDINATES
    # ======================================================

    def extract_coordinates(
        self,
    ) -> None:
        """
        Extract latitude and longitude arrays.
        """

        if self.dataset is None:

            raise RuntimeError(

                "Dataset is not open."

            )

        lon = self.dataset.variables["lon"][:]

        lat = self.dataset.variables["lat"][:]

        self.coordinates = {

            "lon": lon,

            "lat": lat,

        }

        logger.info(

            "Coordinates extracted."

        )
            # ======================================================
    # VALIDATE COORDINATES
    # ======================================================

    def validate_coordinates(
        self,
    ) -> None:
        """
        Validate coordinate arrays.
        """

        if not self.coordinates:

            raise RuntimeError(

                "Coordinates have not been extracted."

            )

        lon = self.coordinates["lon"]

        lat = self.coordinates["lat"]

        if lon.ndim != 1:

            raise ValueError(

                "Longitude must be one-dimensional."

            )

        if lat.ndim != 1:

            raise ValueError(

                "Latitude must be one-dimensional."

            )

        if len(lon) == 0:

            raise ValueError(

                "Longitude array is empty."

            )

        if len(lat) == 0:

            raise ValueError(

                "Latitude array is empty."

            )

        logger.info(

            "Coordinate validation passed."

        )
            # ======================================================
    # COORDINATE SUMMARY
    # ======================================================

    def coordinate_summary(
        self,
    ) -> None:
        """
        Log coordinate information.
        """

        if not self.coordinates:

            raise RuntimeError(

                "Coordinates have not been extracted."

            )

        lon = self.coordinates["lon"]

        lat = self.coordinates["lat"]

        logger.info(

            f"Longitude points : {len(lon)}"

        )

        logger.info(

            f"Latitude points  : {len(lat)}"

        )

        logger.info(

            f"Longitude range  : "

            f"{lon.min()} -> {lon.max()}"

        )

        logger.info(

            f"Latitude range   : "

            f"{lat.min()} -> {lat.max()}"

        )
            # ======================================================
    # EXTRACT PRECIPITATION
    # ======================================================

    def extract_precipitation(
        self,
    ) -> None:
        """
        Extract the precipitation grid.
        """

        if self.dataset is None:

            raise RuntimeError(

                "Dataset is not open."

            )

        precipitation = self.dataset.variables[
            "precipitation"
        ][:]

        self.precipitation = precipitation

        logger.info(

            "Precipitation extracted."

        )
            # ======================================================
    # VALIDATE PRECIPITATION
    # ======================================================

    def validate_precipitation(
        self,
    ) -> None:
        """
        Validate the precipitation array.
        """

        if self.precipitation is None:

            raise RuntimeError(

                "Precipitation has not been extracted."

            )

        if self.precipitation.ndim != 3:

            raise ValueError(

                "Expected a 3-dimensional array."

            )

        if self.precipitation.shape[0] != 1:

            raise ValueError(

                "Expected exactly one time slice."

            )

        logger.info(

            "Precipitation validation passed."

        )
            # ======================================================
    # PRECIPITATION SUMMARY
    # ======================================================

    def precipitation_summary(
        self,
    ) -> None:
        """
        Log precipitation statistics.
        """

        if self.precipitation is None:

            raise RuntimeError(

                "Precipitation has not been extracted."

            )

        grid = self.precipitation

        logger.info(

            f"Shape : {grid.shape}"

        )

        logger.info(

            f"Minimum : {float(grid.min()):.3f}"

        )

        logger.info(

            f"Maximum : {float(grid.max()):.3f}"

        )

        logger.info(

            f"Mean : {float(grid.mean()):.3f}"

        )
            # ======================================================
    # BUILD DATAFRAME
    # ======================================================

    def build_dataframe(
        self,
    ) -> None:
        """
        Convert the precipitation grid into
        a tabular DataFrame.
        """

        if self.precipitation is None:

            raise RuntimeError(

                "Precipitation has not been extracted."

            )

        if not self.coordinates:

            raise RuntimeError(

                "Coordinates have not been extracted."

            )

        precipitation = self.precipitation[0]

        lon = self.coordinates["lon"]

        lat = self.coordinates["lat"]
        longitude_grid, latitude_grid = np.meshgrid(
            lon,
            lat,
            indexing="ij",
        )
        time_variable = self.dataset.variables[
            "time"
        ]

        time_value = nc.num2date(

            time_variable[:][0],

            units=time_variable.units,

        )

        valid_time = pd.Timestamp(

            year=time_value.year,

            month=time_value.month,

            day=time_value.day,

            hour=time_value.hour,

            minute=time_value.minute,

            second=time_value.second,

            tz="UTC",

        )

        self.dataframe = pd.DataFrame(
            {
                "longitude": longitude_grid.ravel(),

                "latitude": latitude_grid.ravel(),

                "valid_time": np.full(

                    precipitation.size,

                    valid_time,

                ),

                "precipitation": precipitation.ravel(),
            }
        )

        logger.info(

            f"DataFrame built: "

            f"{len(self.dataframe):,} rows."

        )

        logger.info(

            f"DataFrame built: "

            f"{len(self.dataframe):,} rows."

        )
            # ======================================================
    # SAVE PARQUET
    # ======================================================

    def save_parquet(
        self,
    ) -> None:
        """
        Save the parsed dataframe as
        a Parquet dataset.
        """

        if self.dataframe is None:
            raise RuntimeError(
                "DataFrame has not been built."
            )

        self.dataframe = self.dataframe.sort_values(

        [

                "longitude",

                "latitude",

        ],

        ignore_index=True,

        )
        table = pa.Table.from_pandas(
            self.dataframe,
            preserve_index=False,
        )

        metadata = {
            "title": self.metadata["title"],
            "doi": self.metadata["doi"],
            "coverage_start": self.metadata["begin_date"],
            "coverage_end": self.metadata["end_date"],
            "production_time": self.metadata["production_time"],
        }

        existing = table.schema.metadata or {}
        merged = {
            **existing,
            **{
                key.encode(): str(value).encode()
                for key, value in metadata.items()
            },
        }

        table = table.replace_schema_metadata(merged)

        # Create output directory if needed.
        self.output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_file = self.output_file.with_suffix(".tmp")
        pq.write_table(
            table,
            temporary_file,
            compression="zstd",
            compression_level=3,
        )
        temporary_file.replace(self.output_file)
        logger.info(
            f"Saved Parquet: "
            f"{self.output_file}"
        )
            # ======================================================
    # CLOSE
    # ======================================================

    def close(
        self,
    ) -> None:
        """
        Close the NetCDF dataset if it is open.
        """

        if self.dataset is not None:

            self.dataset.close()

            self.dataset = None
                # ======================================================
    # CONTEXT MANAGER
    # ======================================================

    def __enter__(
        self,
    ) -> "GPMParser":

        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:

        self.close()