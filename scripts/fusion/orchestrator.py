"""
============================================================
SusBiome Fusion Orchestrator
============================================================

Coordinates the complete data fusion pipeline.

NASA
ERA5
Other Providers
        ↓
Alignment
        ↓
Merge
        ↓
Unified Dataset

============================================================
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.fusion.align import DataAligner
from scripts.fusion.dataset import UnifiedDataset
from scripts.fusion.merge import DatasetMerger


class FusionOrchestrator:
    """
    Production data fusion orchestrator.
    """

    # ======================================================
    # INITIALIZE
    # ======================================================

    def __init__(
        self,
    ) -> None:

        self.aligner = DataAligner()

        self.merger = DatasetMerger()

    # ======================================================
    # LOAD
    # ======================================================

    def load(
        self,
        path: Path,
    ) -> pd.DataFrame:

        return self.aligner.load(

            path

        )

    # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
        *,
        left_path: Path,
        right_path: Path,
        output_path: Path,
    ) -> Path:
        """
        Execute the complete fusion pipeline.
        """

        #
        # Load
        #
        left = self.load(

            left_path

        )

        right = self.load(

            right_path

        )

        #
        # Align
        #
        left = self.aligner.align(
            left
        )

        right = self.aligner.align(
            right
        )

        fused = self.merger.run(
            left=left,
            right=right,
        )

        UnifiedDataset.save(
            fused,
            output_path,
        )

        return output_path
