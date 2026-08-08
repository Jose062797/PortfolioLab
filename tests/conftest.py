"""
Shared test fixtures for Black-Litterman test suite.

Provides synthetic market data and mock yfinance responses so that
tests run offline and deterministically.
"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


@pytest.fixture
def synthetic_prices():
    """
    Generate 500 days of synthetic closing prices for 3 tickers + SPY.

    Returns a DataFrame with DatetimeIndex and columns ['AAPL', 'MSFT', 'GOOGL', 'SPY'].
    Prices follow a random walk with drift so that returns are non-trivial.
    """
    np.random.seed(42)
    n_days = 500
    dates = pd.bdate_range(start="2022-01-03", periods=n_days)

    tickers = ["AAPL", "MSFT", "GOOGL", "SPY"]
    initial_prices = [150.0, 300.0, 2800.0, 450.0]
    daily_drift = [0.0003, 0.0004, 0.0002, 0.00025]
    daily_vol = [0.015, 0.014, 0.018, 0.010]

    data = {}
    for i, ticker in enumerate(tickers):
        returns = np.random.normal(daily_drift[i], daily_vol[i], n_days)
        prices = initial_prices[i] * np.cumprod(1 + returns)
        data[ticker] = prices

    return pd.DataFrame(data, index=dates)


@pytest.fixture
def portfolio_tickers():
    """Standard 3-ticker portfolio (no benchmark)."""
    return ["AAPL", "MSFT", "GOOGL"]


@pytest.fixture
def sample_weights():
    """Sample portfolio weights summing to 1."""
    return {"AAPL": 0.4, "MSFT": 0.35, "GOOGL": 0.25}


@pytest.fixture
def sample_mcaps():
    """Sample market capitalizations."""
    return {"AAPL": 2.5e12, "MSFT": 2.8e12, "GOOGL": 1.8e12}


@pytest.fixture
def mock_yfinance(synthetic_prices):
    """
    Patch yfinance.download to return synthetic prices in OHLCV format.

    Usage in test:
        def test_something(mock_yfinance):
            # yf.download() now returns synthetic data
            ...
    """
    def _make_ohlcv(tickers_arg, **kwargs):
        """Build a multi-level DataFrame that mimics yf.download output."""
        if isinstance(tickers_arg, str):
            tickers_arg = [tickers_arg]

        available = [t for t in tickers_arg if t in synthetic_prices.columns]
        if not available:
            return pd.DataFrame()

        if len(available) == 1:
            ticker = available[0]
            close = synthetic_prices[ticker]
            df = pd.DataFrame({
                'Open': close * 0.99,
                'High': close * 1.01,
                'Low': close * 0.98,
                'Close': close,
                'Volume': np.random.randint(1e6, 1e7, len(close)),
            }, index=synthetic_prices.index)
            return df

        # Multi-ticker: build MultiIndex columns
        arrays = []
        for col_type in ['Open', 'High', 'Low', 'Close', 'Volume']:
            for ticker in available:
                if col_type == 'Close':
                    arrays.append(('Close', ticker))
                elif col_type == 'Volume':
                    arrays.append(('Volume', ticker))
                else:
                    multiplier = {'Open': 0.99, 'High': 1.01, 'Low': 0.98}[col_type]
                    arrays.append((col_type, ticker))

        tuples = []
        data_dict = {}
        for col_type in ['Open', 'High', 'Low', 'Close', 'Volume']:
            for ticker in available:
                col_key = (col_type, ticker)
                tuples.append(col_key)
                if col_type == 'Close':
                    data_dict[col_key] = synthetic_prices[ticker].values
                elif col_type == 'Volume':
                    data_dict[col_key] = np.random.randint(1e6, 1e7, len(synthetic_prices))
                else:
                    multiplier = {'Open': 0.99, 'High': 1.01, 'Low': 0.98}[col_type]
                    data_dict[col_key] = (synthetic_prices[ticker] * multiplier).values

        idx = pd.MultiIndex.from_tuples(tuples, names=['Price', 'Ticker'])
        df = pd.DataFrame(data_dict, index=synthetic_prices.index)
        df.columns = idx
        return df

    with patch('yfinance.download', side_effect=_make_ohlcv) as mock_dl:
        # Also mock yf.Ticker for market cap lookups
        def _make_ticker(symbol):
            t = MagicMock()
            caps = {"AAPL": 2.5e12, "MSFT": 2.8e12, "GOOGL": 1.8e12, "SPY": 4e11}
            t.info = {"marketCap": caps.get(symbol, 1e9)}
            return t

        with patch('yfinance.Ticker', side_effect=_make_ticker):
            yield mock_dl


# ─────────────────────────────────────────────────────────────────────
# Extended universe — used by the AppTest page-layer suite
# (tests/test_pages_portfolio.py). Adds a near-duplicate ETF pair so the
# overlapping-holdings detector can be exercised end-to-end.
# ─────────────────────────────────────────────────────────────────────

# Market caps for the extended universe. ETFs report AUM via totalAssets,
# but the engine reads marketCap first, so a single key is enough here.
_EXTENDED_MCAPS = {
    "AAPL": 2.5e12, "MSFT": 2.8e12, "GOOGL": 1.8e12,
    "SPY": 4e11, "VOO": 3.5e11, "IVV": 3.3e11,
}


def _build_ohlcv(prices, tickers_arg):
    """Build a yf.download-shaped frame (single or MultiIndex) from closes."""
    if isinstance(tickers_arg, str):
        tickers_arg = [tickers_arg]

    available = [t for t in tickers_arg if t in prices.columns]
    if not available:
        return pd.DataFrame()

    multipliers = {'Open': 0.99, 'High': 1.01, 'Low': 0.98}

    if len(available) == 1:
        close = prices[available[0]]
        return pd.DataFrame({
            'Open': close * multipliers['Open'],
            'High': close * multipliers['High'],
            'Low': close * multipliers['Low'],
            'Close': close,
            'Volume': np.full(len(close), 5_000_000),
        }, index=prices.index)

    tuples, data = [], {}
    for col_type in ['Open', 'High', 'Low', 'Close', 'Volume']:
        for ticker in available:
            key = (col_type, ticker)
            tuples.append(key)
            if col_type == 'Close':
                data[key] = prices[ticker].values
            elif col_type == 'Volume':
                data[key] = np.full(len(prices), 5_000_000)
            else:
                data[key] = (prices[ticker] * multipliers[col_type]).values

    df = pd.DataFrame(data, index=prices.index)
    df.columns = pd.MultiIndex.from_tuples(tuples, names=['Price', 'Ticker'])
    return df


@pytest.fixture
def extended_prices():
    """
    Synthetic closes for AAPL, MSFT, GOOGL, SPY plus a near-duplicate ETF
    pair (VOO / IVV).

    VOO and IVV are built as the same price path perturbed by tiny
    independent noise, so their EMPIRICAL return correlation lands well
    above the 0.95 overlap threshold — mirroring the real VOO/IVV pair
    (~0.9997) that motivated the detector.

    Calibration matters here: over the 5-asset universe the pair reads
    ~0.9996 empirically but only ~0.926 after Ledoit-Wolf shrinkage. That
    gap is deliberate — it is what makes a regression to the stored
    (shrunk) covariance detectable instead of silently passing. It is
    asserted directly by test_pages_portfolio.py::test_fixture_discriminates.
    """
    np.random.seed(42)
    n_days = 500
    dates = pd.bdate_range(start="2022-01-03", periods=n_days)

    base = {
        "AAPL": (150.0, 0.0003, 0.015),
        "MSFT": (300.0, 0.0004, 0.014),
        "GOOGL": (2800.0, 0.0002, 0.018),
        "SPY": (450.0, 0.00025, 0.010),
        "VOO": (410.0, 0.00025, 0.010),
    }

    data = {}
    for ticker, (initial, drift, vol) in base.items():
        returns = np.random.normal(drift, vol, n_days)
        data[ticker] = initial * np.cumprod(1 + returns)

    # IVV tracks the same index as VOO: identical path, negligible noise.
    noise = np.random.normal(0.0, 0.0002, n_days)
    data["IVV"] = data["VOO"] * (1 + noise) * (445.0 / 410.0)

    return pd.DataFrame(data, index=dates)


@pytest.fixture
def mock_yfinance_extended(extended_prices):
    """Patch yfinance against the extended universe (see extended_prices)."""
    def _download(tickers_arg, **kwargs):
        return _build_ohlcv(extended_prices, tickers_arg)

    def _ticker(symbol):
        t = MagicMock()
        t.info = {"marketCap": _EXTENDED_MCAPS.get(symbol, 1e9)}
        return t

    with patch('yfinance.download', side_effect=_download) as mock_dl:
        with patch('yfinance.Ticker', side_effect=_ticker):
            yield mock_dl
