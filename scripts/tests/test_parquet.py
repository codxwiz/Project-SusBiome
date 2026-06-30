from pathlib import Path

import pyarrow.parquet as pq

parquet_file = Path(
    "data/silver/gpm/test.parquet"
)

print("=" * 60)
print("VERIFY PARQUET")
print("=" * 60)

if not parquet_file.exists():

    raise FileNotFoundError(

        parquet_file

    )

table = pq.read_table(

    parquet_file

)

print()

print("Rows:")
print(table.num_rows)

print()

print("Columns:")
print(table.column_names)

print()

print("Schema:")
print(table.schema)

print()

print("Metadata:")

metadata = table.schema.metadata or {}

for key, value in metadata.items():

    print(

        key.decode(),

        "=",

        value.decode(),

    )