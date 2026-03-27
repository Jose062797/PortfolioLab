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
