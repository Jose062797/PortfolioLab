"""
Core package of PortfolioLab: framework-independent logic.

    from core.constants import RISK_FREE_RATE
    from core.opt_engine import download_data, optimize_portfolio
    from core.backtest import run_backtest
    from core.pdf_shared import create_allocation_chart
"""

import logging

# Configure package-level logging.
# Libraries should NOT call logging.basicConfig() — that's the application's job.
# But we add a NullHandler so that if the application doesn't configure logging,
# no "No handler found" warnings appear.
logging.getLogger("core").addHandler(logging.NullHandler())
