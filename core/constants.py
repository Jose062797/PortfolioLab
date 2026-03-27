"""
Constants for Black-Litterman Portfolio Optimizer

This module contains all configuration constants used across the application.
Centralizing constants ensures consistency and makes maintenance easier.
"""

# Data Validation Constants
MIN_TICKERS = 2
MAX_TICKERS = 20
MIN_DATE_RANGE_DAYS = 60
MIN_DATA_POINTS = 20
MIN_PORTFOLIO_VALUE = 100
MAX_PORTFOLIO_VALUE = 1e9  # 1 billion USD

# Financial Constants
RISK_FREE_RATE = 0.03  # 3.0% annual (US Treasury 10-year average)
DEFAULT_MARKET_CAP = 1e9  # Default market cap if data unavailable
MIN_WEIGHT_THRESHOLD = 0.001  # Minimum portfolio weight to display (0.1%)
MAX_VIEW_THRESHOLD = 2.0  # 200% sanity check for views
TRADING_DAYS_PER_YEAR = 252  # Trading days for annualization

# Application Constants
BENCHMARK_TICKER = "SPY"  # S&P 500 ETF for market data
RESULTS_FILENAME = "bl_results.json"  # Output file for optimization results
DEFAULT_PORTFOLIO_VALUE = 10000  # Default portfolio value in USD
HEADER_WIDTH = 70  # Character width for console headers

# Historical Analysis Constants
HISTORICAL_PERIOD_YEARS = 5  # Years for historical validation

# Reporting Constants
LOGO_FILENAMES = ['PortfolioLab.png', 'Finance for all.png', 'logo.png']

# Comparison Tolerance Constants
RETURN_COMPARISON_TOLERANCE = 1.0  # Percentage points for return similarity
SHARPE_COMPARISON_TOLERANCE = 0.1  # Absolute difference for Sharpe ratio

# Auto-cleanup Constants
MAX_SAVED_OPTIMIZATIONS = 20  # Maximum number of saved optimization JSON files


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
