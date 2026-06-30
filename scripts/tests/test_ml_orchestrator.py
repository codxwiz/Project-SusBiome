"""
============================================================
ML Orchestrator Test
============================================================
"""

from scripts.ml.orchestrator import MLOrchestrator
from scripts.ml.models import TRAINING_DATASET

print()
print("=" * 60)
print("STARTING ML PIPELINE")
print("=" * 60)
print()

pipeline = MLOrchestrator()

metrics, predictions = pipeline.run(
    dataset_path=TRAINING_DATASET,
)

print(metrics)

print()

print(predictions.head())

print()

print("=" * 60)
print("ML PIPELINE PASSED")
print("=" * 60)