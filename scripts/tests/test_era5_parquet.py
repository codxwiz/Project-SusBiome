"""
============================================================
Verify ERA5 Parquet
============================================================

Verify the generated ERA5 Parquet dataset.

============================================================
"""

from pathlib import Path

import pyarrow.parquet as pq


PARQUET_FILE = Path(
    "data/silver/era5/test.parquet"
)

print()
print("=" * 60)
print("VERIFY ERA5 PARQUET")
print("=" * 60)
print()

if not PARQUET_FILE.exists():

    raise FileNotFoundError(

        f"Parquet file not found:\n{PARQUET_FILE}"

    )

table = pq.read_table(
    PARQUET_FILE
)

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

        f"{key.decode()} = "

        f"{value.decode()}"

    )

print()

print("Preview:")
print(

    table.to_pandas().head()

)

print()

print("=" * 60)
print("PARQUET VERIFIED")
print("=" * 60)