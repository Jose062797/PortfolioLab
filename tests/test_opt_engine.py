"""Tests for core.opt_engine — portfolio optimization engine."""

import numpy as np
import pandas as pd
import pytest

from core.opt_engine import (
    calculate_prior,
    run_black_litterman,
    calculate_markowitz_inputs,
    optimize_portfolio,
    calculate_allocation,
)

class TestCalculateMarkowitzInputs:
    """Test standard Markowitz calculation."""

    def test_markowitz_returns_expected_structure(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """calculate_markowitz_inputs should return (mu, S)."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]

        mu, S = calculate_markowitz_inputs(prices)

        # Expected parameters
        assert isinstance(mu, pd.Series)
        assert len(mu) == len(tickers)
        assert isinstance(S, pd.DataFrame)
        assert S.shape == (len(tickers), len(tickers))


class TestCalculatePrior:
    """Test market prior calculation."""

    def test_returns_expected_structure(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """calculate_prior should return (S, delta, market_prior, prices_clean_with_spy)."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]
        market_prices = synthetic_prices["SPY"]

        S, delta, market_prior, prices_clean = calculate_prior(prices, market_prices, sample_mcaps)

        # Covariance matrix
        assert S.shape == (3, 3)
        # Risk aversion scalar
        assert isinstance(delta, float)
        assert delta > 0
        # Prior returns — one per ticker
        assert len(market_prior) == 3
        for t in tickers:
            assert t in market_prior.index
        # Cleaned prices include SPY column
        assert "SPY" in prices_clean.columns

    def test_prior_returns_are_reasonable(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """Market-implied returns should be in a reasonable range."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]
        market_prices = synthetic_prices["SPY"]

        _, _, market_prior, _ = calculate_prior(prices, market_prices, sample_mcaps)

        for ticker, ret in market_prior.items():
            # Returns should be between -100% and +100%
            assert -1.0 < ret < 1.0, f"{ticker} has unreasonable prior: {ret}"


class TestRunBlackLitterman:
    """Test Black-Litterman model."""

    def test_no_views_equals_prior(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """Without views, posterior should equal prior."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]
        market_prices = synthetic_prices["SPY"]

        S, delta, market_prior, _ = calculate_prior(prices, market_prices, sample_mcaps)
        bl, ret_bl, S_bl = run_black_litterman(S, delta, sample_mcaps, market_prior, None, None)

        assert bl is None
        pd.testing.assert_series_equal(ret_bl, market_prior)

    def test_with_views(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """With views, posterior should differ from prior."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]
        market_prices = synthetic_prices["SPY"]

        S, delta, market_prior, _ = calculate_prior(prices, market_prices, sample_mcaps)

        viewdict = {"AAPL": 0.20}
        intervals = {"AAPL": (0.15, 0.25)}

        bl, ret_bl, S_bl = run_black_litterman(S, delta, sample_mcaps, market_prior, viewdict, intervals)

        assert bl is not None
        # AAPL posterior should shift toward the view
        assert ret_bl["AAPL"] != market_prior["AAPL"]


class TestOptimizePortfolio:
    """Test portfolio optimization."""

    def test_weights_sum_to_one(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """Optimal weights should approximately sum to 1."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]
        market_prices = synthetic_prices["SPY"]

        S, delta, market_prior, _ = calculate_prior(prices, market_prices, sample_mcaps)
        _, ret_bl, S_bl = run_black_litterman(S, delta, sample_mcaps, market_prior, None, None)
        weights, metrics = optimize_portfolio(ret_bl, S_bl)

        total = sum(weights.values())
        assert total == pytest.approx(1.0, abs=0.02)

    def test_metrics_structure(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """Performance metrics should contain expected keys."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]
        market_prices = synthetic_prices["SPY"]

        S, delta, market_prior, _ = calculate_prior(prices, market_prices, sample_mcaps)
        _, ret_bl, S_bl = run_black_litterman(S, delta, sample_mcaps, market_prior, None, None)
        _, metrics = optimize_portfolio(ret_bl, S_bl)

        assert "expected_return" in metrics
        assert "volatility" in metrics
        assert "sharpe_ratio" in metrics
        assert metrics["volatility"] > 0

    def test_target_risk_objective(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """Target Risk objective should produce weights summing to ~1 and respect vol target."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]
        market_prices = synthetic_prices["SPY"]

        S, delta, market_prior, _ = calculate_prior(prices, market_prices, sample_mcaps)
        _, ret_bl, S_bl = run_black_litterman(S, delta, sample_mcaps, market_prior, None, None)
        weights, metrics = optimize_portfolio(
            ret_bl, S_bl, obj_function="Target Risk", target_volatility=0.20
        )

        total = sum(weights.values())
        assert total == pytest.approx(1.0, abs=0.02)
        # Volatility should be at or near the target (within tolerance)
        assert metrics["volatility"] <= 0.22

    def test_l2_gamma_diversifies(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """Higher L2 gamma should produce more diversified (less concentrated) weights."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]
        market_prices = synthetic_prices["SPY"]

        S, delta, market_prior, _ = calculate_prior(prices, market_prices, sample_mcaps)
        _, ret_bl, S_bl = run_black_litterman(S, delta, sample_mcaps, market_prior, None, None)

        weights_low, _ = optimize_portfolio(ret_bl, S_bl, l2_gamma=0.0)
        weights_high, _ = optimize_portfolio(ret_bl, S_bl, l2_gamma=2.0)

        max_low = max(weights_low.values())
        max_high = max(weights_high.values())
        # Higher gamma should produce a lower max weight (more diversified)
        assert max_high <= max_low + 0.01  # slight tolerance

    def test_markowitz_max_sharpe(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """Markowitz inputs should also produce valid optimization results."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]
        market_prices = synthetic_prices["SPY"]

        mu, S = calculate_markowitz_inputs(prices, market_prices=market_prices)
        weights, metrics = optimize_portfolio(mu, S, obj_function="Max Sharpe")

        total = sum(weights.values())
        assert total == pytest.approx(1.0, abs=0.02)
        assert metrics["volatility"] > 0

    def test_min_volatility_objective(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """Min Volatility should produce weights summing to ~1 and lower vol than Max Sharpe."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]
        market_prices = synthetic_prices["SPY"]

        mu, S = calculate_markowitz_inputs(prices, market_prices=market_prices)
        weights_mv, metrics_mv = optimize_portfolio(mu, S, obj_function="Min Variance")
        _, metrics_ms = optimize_portfolio(mu, S, obj_function="Max Sharpe")

        total = sum(weights_mv.values())
        assert total == pytest.approx(1.0, abs=0.02)
        assert metrics_mv["volatility"] > 0
        # Min vol should be <= Max Sharpe vol
        assert metrics_mv["volatility"] <= metrics_ms["volatility"] + 0.01

    def test_target_return_objective(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """Target Return should produce weights summing to ~1 and achieve close to target."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]
        market_prices = synthetic_prices["SPY"]

        mu, S = calculate_markowitz_inputs(prices, market_prices=market_prices)

        # Use a feasible target return (average of expected returns)
        target = float(mu.mean())
        weights, metrics = optimize_portfolio(
            mu, S, obj_function="Minimise Risk for a Given Return", target_return=target
        )

        total = sum(weights.values())
        assert total == pytest.approx(1.0, abs=0.02)
        # Achieved return should be close to target
        assert metrics["expected_return"] == pytest.approx(target, abs=0.02)


class TestCalculateAllocation:
    """Test discrete share allocation."""

    def test_basic_allocation(self, mock_yfinance, synthetic_prices, sample_mcaps):
        """Allocation should produce shares and leftover cash."""
        tickers = list(sample_mcaps.keys())
        prices = synthetic_prices[tickers]
        market_prices = synthetic_prices["SPY"]

        S, delta, market_prior, prices_clean = calculate_prior(prices, market_prices, sample_mcaps)
        _, ret_bl, S_bl = run_black_litterman(S, delta, sample_mcaps, market_prior, None, None)
        weights, _ = optimize_portfolio(ret_bl, S_bl)

        prices_for_alloc = prices_clean[[t for t in tickers if t in prices_clean.columns]]
        allocation, leftover = calculate_allocation(weights, prices_for_alloc, 50000)

        assert isinstance(allocation, dict)
        assert leftover >= 0
        # At least one ticker should get shares with $50k
        assert len(allocation) > 0

