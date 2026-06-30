"""
============================================================
Test ERA5 Parser
============================================================

Runs the complete ERA5 parsing pipeline.

============================================================
"""

from pathlib import Path

from scripts.sources.era5.parse_era5 import ERA5Parser


INPUT_FILE = Path(
    "data/bronze/era5/test.nc"
)

OUTPUT_FILE = Path(
    "data/silver/era5/test.parquet"
)


with ERA5Parser(

    input_file=INPUT_FILE,

    output_file=OUTPUT_FILE,

) as parser:

    #
    # Open
    #
    parser.open_dataset()

    #
    # Validate
    #
    parser.validate()

    #
    # Metadata
    #
    parser.extract_metadata()

    parser.metadata_summary()

    #
    # Coordinates
    #
    parser.extract_coordinates()

    parser.coordinate_summary()

    #
    # Extract Temperature
    #
    parser.extract_variable(
        "t2m"
    )

    parser.variable_summary()

    #
    # DataFrame
    #
    parser.build_dataframe()

    parser.dataframe_summary()

    #
    # Save
    #
    parser.save_parquet()


print()

print("=" * 60)

print("ERA5 PARSER TEST PASSED")

print("=" * 60)