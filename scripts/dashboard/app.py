"""
==============================================================
Project SusBiome
Dashboard Application
==============================================================

Main entry point for the Project SusBiome Dashboard.

Responsibilities
----------------
• Verify datasets
• Initialize dashboard
• Build complete UI
• Display startup errors

Run
---
streamlit run scripts/dashboard/app.py

Author : Project SusBiome
==============================================================
"""

from __future__ import annotations

import logging

import streamlit as st  # type: ignore[import]

from scripts.dashboard.layout import (
    DashboardLayout,
)

from scripts.dashboard.loader import (
    DashboardLoader,
)

logger = logging.getLogger(__name__)


# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(

    level=logging.INFO,

    format=(

        "%(asctime)s | "

        "%(levelname)s | "

        "%(name)s | "

        "%(message)s"

    ),

)


# ==========================================================
# APPLICATION
# ==========================================================

class DashboardApplication:
    """
    Project SusBiome Dashboard.
    """

    def __init__(
        self,
    ) -> None:

        self.loader = DashboardLoader()

        self.layout = DashboardLayout()

    # ======================================================
    # STARTUP CHECK
    # ======================================================

    def startup(
        self,
    ) -> bool:
        """
        Verify dashboard datasets.
        """

        status = self.loader.status()

        if not status.prediction:

            st.error(

                "Prediction dataset not found."

            )

            logger.error(

                "Prediction dataset missing."

            )

            return False

        if not status.risk:

            st.error(

                "Risk dataset not found."

            )

            logger.error(

                "Risk dataset missing."

            )

            return False

        logger.info(
            "Dashboard startup passed."
        )

        return True

    # ======================================================
    # BUILD
    # ======================================================

    def build(
        self,
    ) -> None:
        """
        Build dashboard.
        """

        if not self.startup():

            st.stop()

        self.layout.build()

    # ======================================================
    # RUN
    # ======================================================

    def run(
        self,
    ) -> None:
        """
        Launch dashboard.
        """

        logger.info(
            "Launching Dashboard."
        )

        try:

            self.build()

            logger.info(
                "Dashboard ready."
            )

        except Exception as error:

            logger.exception(
                "Dashboard failed."
            )

            st.exception(
                error,
            )


# ==========================================================
# MAIN
# ==========================================================

def main() -> None:
    """
    Dashboard entry point.
    """

    DashboardApplication().run()


if __name__ == "__main__":

    main()