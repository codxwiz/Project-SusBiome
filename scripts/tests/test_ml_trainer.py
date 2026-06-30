"""
============================================================
ML Trainer Test
============================================================
"""

from scripts.ml.trainer import MLTrainer

print()
print("=" * 60)
print("ML TRAINER TEST")
print("=" * 60)
print()

trainer = MLTrainer()

metrics = trainer.train()

print(metrics)

print()

print("=" * 60)
print("ML TRAINER PASSED")
print("=" * 60)