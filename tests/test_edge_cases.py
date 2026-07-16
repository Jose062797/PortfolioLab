"""
Numerical edge cases for the optimization engine (audit D1.4).

Verifies that degenerate inputs fail gracefully with OptimizationError
(never a bare crash) and that near-degenerate inputs still produce
valid portfolios.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from core.constants import OptimizationError, DataDownloadError
from core.opt_engine import calculate_markowitz_inputs, optimize_portfolio, download_data


@pytest.fixture
def low_return_inputs():
    """Expected returns all BELOW the 3% risk-free rate, valid covariance."""
    tickers = ["A", "B", "C"]
    mu = pd.Series([0.01, 0.02, 0.025], index=tickers)
    cov = pd.DataFrame(
        np.array([
            [0.04, 0.01, 0.00],
            [0.01, 0.03, 0.01],
            [0.00, 0.01, 0.05],
        ]),
        index=tickers, columns=tickers,
    )
    return mu, cov


@pytest.fixture
def valid_inputs():
    tickers = ["A", "B", "C"]
    mu = pd.Series([0.08, 0.12, 0.15], index=tickers)
    cov = pd.DataFrame(
        np.array([
            [0.04, 0.01, 0.00],
            [0.01, 0.09, 0.02],
            [0.00, 0.02, 0.16],
        ]),
        index=tickers, columns=tickers,
    )
    return mu, cov


class TestReturnsBelowRiskFree:
    def test_max_sharpe_raises_domain_error(self, low_return_inputs):
        """No asset beats the risk-free rate → typed error, not a crash."""
        mu, cov = low_return_inputs
        with pytest.raises(OptimizationError):
            optimize_portfolio(mu, cov, obj_function="Max Sharpe")

    def test_min_variance_still_works(self, low_return_inputs):
        """Min Variance does not depend on the risk-free rate."""
        mu, cov = low_return_inputs
        weights, metrics = optimize_portfolio(mu, cov, obj_function="Min Variance")
        assert sum(weights.values()) == pytest.approx(1.0, abs=0.02)
        assert metrics["volatility"] > 0


class TestInfeasibleTargets:
    def test_target_return_above_max_raises(self, valid_inputs):
        mu, cov = valid_inputs
        with pytest.raises(OptimizationError):
            optimize_portfolio(
                mu, cov, obj_function="Minimise Risk for a Given Return",
                target_return=float(mu.max()) + 0.10,
            )

    def test_target_volatility_below_min_raises_or_clamps(self, valid_inputs):
        """A target volatility below the min-variance point is unreachable."""
        mu, cov = valid_inputs
        _, m_minv = optimize_portfolio(mu, cov, obj_function="Min Variance")
        impossible_vol = m_minv["volatility"] * 0.5
        with pytest.raises(OptimizationError):
            optimize_portfolio(
                mu, cov, obj_function="Maximise Return for a Given Risk",
                target_volatility=impossible_vol,
            )


class TestNearSingularCovariance:
    def test_two_almost_identical_assets(self):
        """Nearly collinear assets must not blow up the solver."""
        np.random.seed(7)
        n = 500
        base = np.random.normal(0.0005, 0.01, n)
        prices = pd.DataFrame({
            "X": 100 * np.cumprod(1 + base),
            "Y": 100 * np.cumprod(1 + base + np.random.normal(0, 1e-5, n)),
            "Z": 100 * np.cumprod(1 + np.random.normal(0.0004, 0.012, n)),
        }, index=pd.bdate_range("2022-01-03", periods=n))
        market = pd.Series(
            450 * np.cumprod(1 + np.random.normal(0.0003, 0.009, n)),
            index=prices.index, name="SPY",
        )

        mu, S = calculate_markowitz_inputs(prices, market)
        weights, metrics = optimize_portfolio(mu, S, obj_function="Min Variance")

        assert sum(weights.values()) == pytest.approx(1.0, abs=0.02)
        assert all(w >= -1e-6 for w in weights.values())
        assert np.isfinite(metrics["volatility"])


class TestBadTickerDetection:
    """A nonexistent/delisted ticker returns an all-NaN column from yfinance.

    The engine must reject it with a clear DataDownloadError naming the
    ticker, instead of letting NaN poison the solver downstream.
    """

    def _mock_download(self, good_tickers, bad_tickers):
        n = 300
        idx = pd.bdate_range("2023-01-02", periods=n)
        rng = np.random.default_rng(0)
        tuples, data = [], {}
        for t in good_tickers + bad_tickers:
            tuples.append(("Close", t))
            if t in bad_tickers:
                data[("Close", t)] = np.full(n, np.nan)
            else:
                data[("Close", t)] = 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, n))
        df = pd.DataFrame(data, index=idx)
        df.columns = pd.MultiIndex.from_tuples(tuples, names=["Price", "Ticker"])
        return df

    def test_all_nan_column_raises_with_ticker_name(self):
        mock_df = self._mock_download(["AAPL", "MSFT"], ["XXXXFAKE99"])
        with patch("yfinance.download", return_value=mock_df):
            with pytest.raises(DataDownloadError, match="XXXXFAKE99"):
                download_data(["AAPL", "MSFT", "XXXXFAKE99"], None)

    def test_all_valid_tickers_pass(self):
        mock_df = self._mock_download(["AAPL", "MSFT"], [])
        with patch("yfinance.download", return_value=mock_df):
            prices, market = download_data(["AAPL", "MSFT"], None)
        assert list(prices.columns) == ["AAPL", "MSFT"]
        assert not prices.isna().any().any()


class TestUnequalHistories:
    def test_nan_head_ticker_survives_pipeline(self, synthetic_prices):
        """A ticker with a shorter history (NaN head) must still optimize.

        Covariance uses pairwise-available data (Ledoit-Wolf on NaN-tolerant
        returns), matching the notebook behaviour documented in CLAUDE.md.
        """
        prices = synthetic_prices[["AAPL", "MSFT", "GOOGL"]].copy()
        prices.iloc[:200, prices.columns.get_loc("GOOGL")] = np.nan
        market = synthetic_prices["SPY"]

        mu, S = calculate_markowitz_inputs(prices, market)

        assert not mu.isna().any(), "expected returns must not contain NaN"
        assert not S.isna().any().any(), "covariance must not contain NaN"

        weights, metrics = optimize_portfolio(mu, S, obj_function="Min Variance")
        assert sum(weights.values()) == pytest.approx(1.0, abs=0.02)
        assert np.isfinite(metrics["volatility"])
