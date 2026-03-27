"""
Core package for Black-Litterman Portfolio Optimizer.

This __init__.py enables clean imports from the core package:
    from core.constants import RISK_FREE_RATE
    from core.opt_engine import download_data, calculate_prior
    from core.opt import download_data  # backward compat (re-exports opt_engine)
    from core.backtest import run_backtest
    from core.pdf_shared import create_prior_chart
"""

import logging

# Configure package-level logging.
# Libraries should NOT call logging.basicConfig() — that's the application's job.
# But we add a NullHandler so that if the application doesn't configure logging,
# no "No handler found" warnings appear.
logging.getLogger("core").addHandler(logging.NullHandler())
