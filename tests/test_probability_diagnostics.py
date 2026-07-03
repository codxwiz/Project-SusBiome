from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from scripts.ml.evaluation import probability_diagnostics


class ProbabilityDiagnosticTests(unittest.TestCase):
    def test_perfect_probabilities_have_zero_brier_score(self):
        result = probability_diagnostics(
            np.array([0.0, 1.0, 0.0, 1.0]),
            pd.Series([0, 1, 0, 1]),
        )

        self.assertEqual(result["brier_score"], 0.0)
        self.assertEqual(result["expected_calibration_error"], 0.0)
        self.assertFalse(result["calibrated_probability"])

    def test_misaligned_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            probability_diagnostics(np.array([0.5]), pd.Series([0, 1]))


if __name__ == "__main__":
    unittest.main()
