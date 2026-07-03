from __future__ import annotations

import unittest

import pandas as pd

from scripts.quality.chirps_crosscheck import comparison_metrics


class ChirpsCrosscheckTests(unittest.TestCase):
    def test_comparison_metrics_preserve_bias_direction(self):
        frame = pd.DataFrame(
            {
                "chirps_precipitation_mm": [0.0, 10.0, 20.0],
                "gpm_precipitation_mm": [1.0, 12.0, 23.0],
            }
        )
        result = comparison_metrics(frame)

        self.assertEqual(result["days"], 3)
        self.assertEqual(result["bias_mm"], 2.0)
        self.assertAlmostEqual(result["correlation"], 1.0)

    def test_empty_comparison_is_explicit(self):
        result = comparison_metrics(
            pd.DataFrame(
                {
                    "chirps_precipitation_mm": [None],
                    "gpm_precipitation_mm": [None],
                }
            )
        )
        self.assertEqual(result["days"], 0)
        self.assertIsNone(result["correlation"])


if __name__ == "__main__":
    unittest.main()
