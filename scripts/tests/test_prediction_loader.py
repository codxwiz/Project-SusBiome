"""
==============================================================
Prediction Loader Test
==============================================================

Tests the PredictionLoader.

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import pprint

from scripts.prediction.loader import (
    PredictionLoader,
)

print()
print("=" * 60)
print("PREDICTION LOADER TEST")
print("=" * 60)
print()

loader = PredictionLoader()

print("Initial Status")
print("-" * 20)

pprint.pprint(
    loader.status()
)

print()

models = loader.load_all()

print("Loaded Models")
print("-" * 20)

for name, model in models.items():

    print(
        f"{name:<10} : {type(model).__name__}"
    )

print()

print("Cache Status")
print("-" * 20)

pprint.pprint(
    loader.status()
)

assert loader.ready()

print()
print("=" * 60)
print("PREDICTION LOADER PASSED")
print("=" * 60)