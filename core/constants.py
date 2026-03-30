"""
Constants for Black-Litterman Portfolio Optimizer

This module contains all configuration constants used across the application.
Centralizing constants ensures consistency and makes maintenance easier.
"""

# Data Validation Constants
MIN_TICKERS = 2
MAX_TICKERS = 20
MIN_DATA_POINTS = 20
MIN_PORTFOLIO_VALUE = 100
MAX_PORTFOLIO_VALUE = 1e9  # 1 billion USD

# Financial Constants
RISK_FREE_RATE = 0.03  # 3.0% annual (standard risk-free rate for portfolio optimization)
MIN_WEIGHT_THRESHOLD = 0.001  # Minimum portfolio weight to display (0.1%)
MAX_VIEW_THRESHOLD = 2.0  # 200% sanity check for views
TRADING_DAYS_PER_YEAR = 252  # Trading days for annualization

# Application Constants
BENCHMARK_TICKER = "SPY"  # S&P 500 ETF for market data

# Historical Analysis Constants
HISTORICAL_PERIOD_YEARS = 5  # Years for historical validation

# Reporting Constants
# Comparison Tolerance Constants
RETURN_COMPARISON_TOLERANCE = 1.0  # Percentage points for return similarity
SHARPE_COMPARISON_TOLERANCE = 0.1  # Absolute difference for Sharpe ratio


# ===== Domain Exceptions =====
class OptimizationError(Exception):
    """Raised when portfolio optimization fails (constraints, numerical instability)."""
    pass


class DataDownloadError(Exception):
    """Raised when market data download fails after all retries."""
    pass


class InsufficientDataError(Exception):
    """Raised when downloaded data has insufficient observations."""
    pass
