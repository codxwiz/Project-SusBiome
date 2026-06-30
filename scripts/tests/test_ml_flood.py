"""
============================================================
Flood Model Test
============================================================
"""

from scripts.ml.dataset import MLDataset
from scripts.ml.models import FEATURE_DATASET, FLOOD_TARGET
from scripts.ml.flood import FloodModel

print()
print("=" * 60)
print("FLOOD MODEL TEST")
print("=" * 60)
print()

X_train, X_valid, X_test, y_train, y_valid, y_test = MLDataset.build(
    path=FEATURE_DATASET,
    target=FLOOD_TARGET,
)

model = FloodModel()

model.train(X_train, y_train)

metrics = model.evaluate(X_test, y_test)

model.save()

print(metrics)

print()

print("=" * 60)
print("FLOOD MODEL PASSED")
print("=" * 60)