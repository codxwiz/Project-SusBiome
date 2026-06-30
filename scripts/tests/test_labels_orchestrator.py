"""
============================================================
Label Orchestrator Test
============================================================
"""

from pathlib import Path

import pandas as pd

from scripts.labels.orchestrator import LabelOrchestrator


print()
print("=" * 60)
print("STARTING LABEL ENGINEERING")
print("=" * 60)
print()

pipeline = LabelOrchestrator()

output = pipeline.run()

print()

print("Output")

print(output)

print()

df = pd.read_parquet(output)

print(df.head())

print()

print("=" * 60)
print("LABEL ENGINEERING PASSED")
print("=" * 60)