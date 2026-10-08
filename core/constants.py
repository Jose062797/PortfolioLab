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

# Yahoo Finance symbols: letters, digits and . - ^ = (BRK-B, BF.B, ^GSPC,
# BTC-USD, EURUSD=X). Both pages and validate_inputs check it, so arbitrary
# text never reaches a download or the page HTML (audit D5.3, B5-07).
TICKER_PATTERN = r"[A-Z0-9.\-^=]{1,15}"

# Plain-language names of the four optimization objectives, shown in the app
# and the PDF. The keys are the engine's names (core/opt_engine.
# optimize_portfolio), which stay the values everywhere else. Black-Litterman
# always uses Max Sharpe.
OBJECTIVE_LABELS = {
    "Min Variance": "Lowest risk",
    "Max Sharpe": "Best return for the risk",
    "Maximise Return for a Given Risk": "Highest return within a risk limit",
    "Minimise Risk for a Given Return": "Lowest risk for a target return",
}


def goal_text(obj_function: str, target_volatility=None, target_return=None) -> str:
    """
    An objective in plain words, with its target when it has one
    ("Highest return within a risk limit of 12.5%"). The Home page, the
    Portfolio page and the PDF all word it this way.
    """
    text = OBJECTIVE_LABELS.get(obj_function, obj_function)
    if obj_function == "Maximise Return for a Given Risk" and target_volatility is not None:
        text += f" of {target_volatility * 100:g}%"
    elif obj_function == "Minimise Risk for a Given Return" and target_return is not None:
        text += f" of {target_return * 100:g}%"
    return text

# Asset colors, ordered so neighboring pie slices differ, covering MAX_TICKERS
# (20) with lighter and darker shades of the brand hues. The web charts
# (utils/visualizations.py) and the PDF (core/pdf_shared.py) hand them out in
# the same order, so an asset has the same color in both.
ASSET_COLORS = [
    "#2E6FC7", "#10B981", "#F59E0B", "#8DB8F2", "#0A1628",
    "#5B93E0", "#34D399", "#FBBF24", "#64748B", "#1E5AB3",
    "#A7F3D0", "#FDE68A", "#94A3B8", "#C7DBF7", "#059669",
    "#D97706", "#334155", "#3B82F6", "#6EE7B7", "#CBD5E1",
]

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
