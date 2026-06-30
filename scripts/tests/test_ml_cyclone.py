"""
============================================================
Cyclone Model Test
============================================================
"""

from scripts.ml.dataset import MLDataset
from scripts.ml.models import FEATURE_DATASET, CYCLONE_TARGET
from scripts.ml.cyclone import CycloneModel

print()
print("=" * 60)
print("CYCLONE MODEL TEST")
print("=" * 60)
print()

X_train, X_valid, X_test, y_train, y_valid, y_test = MLDataset.build(
    path=FEATURE_DATASET,
    target=CYCLONE_TARGET,
)

model = CycloneModel()

model.train(X_train, y_train)

metrics = model.evaluate(X_test, y_test)

model.save()

print(metrics)

print()

print("=" * 60)
print("CYCLONE MODEL PASSED")
print("=" * 60)