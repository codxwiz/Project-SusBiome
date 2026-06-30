"""
============================================================
ERA5 NetCDF Parser
============================================================

Parses ERA5 NetCDF datasets into Silver Parquet.

Pipeline

NetCDF
    ↓
Validation
    ↓
Metadata
    ↓
Coordinates
    ↓
Variable
    ↓
DataFrame
    ↓
Parquet

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


logger = logging.getLogger(
    "susbiome.era5.parser"
)

if not logger.handlers:

    logger.setLevel(
        logging.INFO
    )

    console = logging.StreamHandler()

    console.setFormatter(

        logging.Formatter(

            "%(asctime)s | %(levelname)s | %(message)s"

        )

    )

    logger.addHandler(
        console
    )


class ERA5Parser:
    """
    Production ERA5 parser.
    """

    # ======================================================
    # INITIALIZE
    # ======================================================

    def __init__(
        self,
        *,
        input_file: Path,
        output_file: Path,
    ) -> None:

        self.input_file = Path(
            input_file
        )

        self.output_file = Path(
            output_file
        )

        self.dataset = None

        self.metadata = {}

        self.coordinates = {}

        self.variable_name = None

        self.variable = None

        self.dataframe = None

    # ======================================================
    # OPEN DATASET
    # ======================================================

    def open_dataset(
        self,
    ) -> None:

        logger.info(

            f"Opening {self.input_file}"

        )

        self.dataset = nc.Dataset(

            self.input_file,

            mode="r",

        )

        logger.info(

            "Dataset opened successfully."

        )

    # ======================================================
    # VALIDATE
    # ======================================================

    def validate(
        self,
    ) -> None:

        if self.dataset is None:

            raise RuntimeError(

                "Dataset is not open."

            )

        required = {

            "latitude",

            "longitude",

            "valid_time",

        }

        missing = [

            item

            for item in required

            if item not in self.dataset.variables

        ]

        if missing:

            raise RuntimeError(

                "Missing variables: "

                + ", ".join(missing)

            )

        logger.info(

            "Dataset validation passed."

        )

    # ======================================================
    # METADATA
    # ======================================================

    def extract_metadata(
        self,
    ) -> None:

        if self.dataset is None:

            raise RuntimeError(

                "Dataset is not open."

            )

        self.metadata = {

            name: getattr(

                self.dataset,

                name,

            )

            for name in self.dataset.ncattrs()

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

        logger.info(

            "Metadata"

        )

        for key, value in self.metadata.items():

            logger.info(

                f"{key}: {value}"

            )

    # ======================================================
    # COORDINATES
    # ======================================================

    def extract_coordinates(
        self,
    ) -> None:

        if self.dataset is None:

            raise RuntimeError(

                "Dataset is not open."

            )

        self.coordinates = {

            "longitude":

                self.dataset.variables[
                    "longitude"
                ][:],

            "latitude":

                self.dataset.variables[
                    "latitude"
                ][:],

        }

        logger.info(

            "Coordinates extracted."

        )

    # ======================================================
    # COORDINATE SUMMARY
    # ======================================================

    def coordinate_summary(
        self,
    ) -> None:

        lon = self.coordinates[
            "longitude"
        ]

        lat = self.coordinates[
            "latitude"
        ]

        logger.info(

            f"Longitude : {len(lon)}"

        )

        logger.info(

            f"Latitude : {len(lat)}"

        )

        logger.info(

            f"Longitude Range : "

            f"{lon.min()} -> {lon.max()}"

        )

        logger.info(

            f"Latitude Range : "

            f"{lat.min()} -> {lat.max()}"

        )
            # ======================================================
    # EXTRACT VARIABLE
    # ======================================================

    def extract_variable(
        self,
        variable_name: str,
    ) -> None:
        """
        Extract any ERA5 variable.
        """

        if self.dataset is None:

            raise RuntimeError(

                "Dataset is not open."

            )

        if variable_name not in self.dataset.variables:

            raise ValueError(

                f"Variable not found: "

                f"{variable_name}"

            )

        self.variable_name = variable_name

        self.variable = self.dataset.variables[
            variable_name
        ][:]

        logger.info(

            f"{variable_name} extracted."

        )

    # ======================================================
    # VARIABLE SUMMARY
    # ======================================================

    def variable_summary(
        self,
    ) -> None:
        """
        Print variable statistics.
        """

        if self.variable is None:

            raise RuntimeError(

                "Variable has not been extracted."

            )

        variable = self.dataset.variables[
            self.variable_name
        ]

        logger.info(

            f"Variable : "

            f"{self.variable_name}"

        )

        logger.info(

            f"Long Name : "

            f"{getattr(variable,'long_name','')}"

        )

        logger.info(

            f"Units : "

            f"{getattr(variable,'units','')}"

        )

        logger.info(

            f"Shape : "

            f"{self.variable.shape}"

        )

        logger.info(

            f"Minimum : "

            f"{float(np.nanmin(self.variable)):.3f}"

        )

        logger.info(

            f"Maximum : "

            f"{float(np.nanmax(self.variable)):.3f}"

        )

        logger.info(

            f"Mean : "

            f"{float(np.nanmean(self.variable)):.3f}"

        )

    # ======================================================
    # BUILD DATAFRAME
    # ======================================================

    def build_dataframe(
        self,
    ) -> None:
        """
        Build one DataFrame from the ERA5 grid.
        """

        if self.variable is None:

            raise RuntimeError(

                "Variable has not been extracted."

            )

        longitude = self.coordinates[
            "longitude"
        ]

        latitude = self.coordinates[
            "latitude"
        ]

        #
        # Remove time dimension.
        #
        grid = self.variable[0]
        valid_time = pd.to_datetime(

            self.dataset.variables[
                "valid_time"
            ][:][0],

            unit="s",

            utc=True,

        )

        #
        # Vectorized coordinate generation.
        #
        lon_grid, lat_grid = np.meshgrid(

            longitude,

            latitude,

            indexing="xy",

        )

        dataframe = pd.DataFrame(

    {

        "longitude":

            lon_grid.ravel(),

        "latitude":

            lat_grid.ravel(),

        "valid_time":

            np.full(

                grid.size,

                valid_time,

            ),

        "value":

            grid.ravel(),

    }

)

        self.dataframe = dataframe

        logger.info(

            f"DataFrame built: "

            f"{len(dataframe):,} rows."

        )

    # ======================================================
    # DATAFRAME SUMMARY
    # ======================================================

    def dataframe_summary(
        self,
    ) -> None:
        """
        Print DataFrame information.
        """

        if self.dataframe is None:

            raise RuntimeError(

                "DataFrame has not been built."

            )

        logger.info(

            f"Rows : "

            f"{len(self.dataframe):,}"

        )

        logger.info(

            f"Columns : "

            f"{list(self.dataframe.columns)}"

        )

        logger.info(

            "Preview"

        )

        logger.info(

            "\n"

            + str(

                self.dataframe.head()

            )

        )
            # ======================================================
    # SAVE PARQUET
    # ======================================================

    def save_parquet(
        self,
    ) -> None:
        """
        Save the DataFrame as a Parquet dataset.
        """

        if self.dataframe is None:

            raise RuntimeError(

                "DataFrame has not been built."

            )

        self.output_file.parent.mkdir(

            parents=True,

            exist_ok=True,

        )

        table = pa.Table.from_pandas(

            self.dataframe,

            preserve_index=False,

        )

        variable = self.dataset.variables[
            self.variable_name
        ]

        metadata = {

            "variable":

                self.variable_name,

            "long_name":

                str(

                    getattr(

                        variable,

                        "long_name",

                        "",

                    )

                ),

            "units":

                str(

                    getattr(

                        variable,

                        "units",

                        "",

                    )

                ),

            "provider":

                "ECMWF",

            "dataset":

                "ERA5",

        }

        existing = (

            table.schema.metadata

            or {}

        )

        encoded = {

            **existing,

            **{

                key.encode():

                value.encode()

                for key, value

                in metadata.items()

            }

        }

        table = table.replace_schema_metadata(

            encoded

        )

        pq.write_table(

            table,

            self.output_file,

            compression="zstd",

        )

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
        Close the NetCDF dataset.
        """

        if self.dataset is not None:

            self.dataset.close()

            self.dataset = None

    # ======================================================
    # CONTEXT MANAGER
    # ======================================================

    def __enter__(
        self,
    ) -> "ERA5Parser":

        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:

        self.close()