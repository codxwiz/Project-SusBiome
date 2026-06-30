"""
============================================================
ML Predictor Test
============================================================
"""

from pathlib import Path

import pandas as pd

from scripts.ml.predictor import MLPredictor

INPUT = Path("data/gold/features.parquet")

print()
print("=" * 60)
print("ML PREDICTOR TEST")
print("=" * 60)
print()

df = pd.read_parquet(INPUT)

predictor = MLPredictor()

result = predictor.predict(df)

print(result.head())

print()

print("=" * 60)
print("ML PREDICTOR PASSED")
print("=" * 60)