from pathlib import Path

from scripts.sources.nasa.gpm.parse_gpm import GPMParser

input_file = Path(
    "bronze/nasa/gpm/sample/"
    "3B-DAY.MS.MRG.3IMERG.20240701.V07B.nc4"
)

output_file = Path(
    "data/silver/gpm/test.parquet"
)

with GPMParser(
    input_file=input_file,
    output_file=output_file,
) as parser:

    parser.open_dataset()

    parser.validate()

    parser.extract_metadata()

    parser.metadata_summary()

    parser.extract_coordinates()

    parser.validate_coordinates()

    parser.coordinate_summary()

    parser.extract_precipitation()

    parser.validate_precipitation()

    parser.precipitation_summary()
    
    parser.build_dataframe()

    print(parser.dataframe.head())

    print(parser.dataframe.tail())
    
    parser.save_parquet()