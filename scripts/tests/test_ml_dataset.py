"""
============================================================
ML Dataset Test
============================================================
"""

from scripts.ml.dataset import MLDataset
from scripts.ml.models import TRAINING_DATASET, FLOOD_TARGET

print()
print("=" * 60)
print("ML DATASET TEST")
print("=" * 60)
print()

X_train, X_valid, X_test, y_train, y_valid, y_test = MLDataset.build(
    path=TRAINING_DATASET,
    target=FLOOD_TARGET,
)

print("Train :", X_train.shape)
print("Validation :", X_valid.shape)
print("Test :", X_test.shape)

print()

print("=" * 60)
print("ML DATASET PASSED")
print("=" * 60)