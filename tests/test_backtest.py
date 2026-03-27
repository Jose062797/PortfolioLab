"""Tests for core.backtest — unified backtest engine."""

import numpy as np
import pandas as pd
import pytest

from core.backtest import (
    _calculate_annualized_metrics,
    run_backtest,
    BacktestResult,
    BacktestMetrics,
)


class TestCalculateAnnualizedMetrics:
    """Test the annualized metrics calculator."""

    def test_positive_returns(self):
        """Metrics should be computed correctly for positive returns."""
        np.random.seed(42)
        daily_returns = pd.Series(np.random.normal(0.0005, 0.01, 252))
        cumulative_values = (1 + daily_returns).cumprod() * 10000
        total_return = 0.12  # 12%
        n_years = 1.0

        metrics = _calculate_annualized_metrics(daily_returns, cumulative_values, total_return, n_years)

        assert isinstance(metrics, BacktestMetrics)
        assert metrics.annualized_return == pytest.approx(12.0, abs=0.1)
        assert metrics.annualized_volatility > 0
        assert isinstance(metrics.sharpe_ratio, float)

    def test_zero_years(self):
        """Zero years should produce zero return."""
        daily_returns = pd.Series([0.01, -0.01, 0.02])
        cumulative_values = (1 + daily_returns).cumprod() * 10000
        metrics = _calculate_annualized_metrics(daily_returns, cumulative_values, 0.05, n_years=0)
        assert metrics.annualized_return == 0

    def test_zero_volatility(self):
        """Zero volatility should produce zero Sharpe."""
        daily_returns = pd.Series([0.0, 0.0, 0.0])
        cumulative_values = (1 + daily_returns).cumprod() * 10000
        metrics = _calculate_annualized_metrics(daily_returns, cumulative_values, 0.0, n_years=1.0)
        assert metrics.sharpe_ratio == 0


class TestRunBacktest:
    """Test the main backtest engine."""

    def test_basic_backtest(self, synthetic_prices, portfolio_tickers, sample_weights):
        """Backtest should return a valid BacktestResult."""
        result = run_backtest(
            prices=synthetic_prices,
            weights=sample_weights,
            tickers=portfolio_tickers,
            portfolio_value=10000,
            benchmark_col="SPY",
        )

        assert result is not None
        assert isinstance(result, BacktestResult)
        assert len(result.dates) == len(synthetic_prices)
        assert len(result.portfolio_values) == len(synthetic_prices)
        assert len(result.benchmark_values) == len(synthetic_prices)

    def test_insufficient_data(self, synthetic_prices, portfolio_tickers, sample_weights):
        """Backtest with too few data points should return None."""
        short_prices = synthetic_prices.head(5)
        result = run_backtest(
            prices=short_prices,
            weights=sample_weights,
            tickers=portfolio_tickers,
            portfolio_value=10000,
            benchmark_col="SPY",
            min_data_points=100,
        )
        assert result is None

    def test_missing_benchmark(self, synthetic_prices, portfolio_tickers, sample_weights):
        """Missing benchmark column should return None."""
        prices_no_spy = synthetic_prices.drop(columns=["SPY"])
        result = run_backtest(
            prices=prices_no_spy,
            weights=sample_weights,
            tickers=portfolio_tickers,
            portfolio_value=10000,
            benchmark_col="SPY",
        )
        assert result is None

    def test_to_dict(self, synthetic_prices, portfolio_tickers, sample_weights):
        """to_dict should return all expected keys."""
        result = run_backtest(
            prices=synthetic_prices,
            weights=sample_weights,
            tickers=portfolio_tickers,
            portfolio_value=10000,
            benchmark_col="SPY",
        )
        d = result.to_dict()

        expected_keys = [
            'portfolio_values', 'spy_values', 'portfolio_pct', 'spy_pct',
            'dates', 'return', 'volatility', 'sharpe', 'max_drawdown', 'sortino', 'calmar',
            'spy_return', 'spy_volatility', 'spy_sharpe', 'spy_max_drawdown', 'spy_sortino', 'spy_calmar', 'period',
        ]
        for key in expected_keys:
            assert key in d, f"Missing key: {key}"

    def test_portfolio_value_starts_correct(self, synthetic_prices, portfolio_tickers, sample_weights):
        """First portfolio value should be close to initial portfolio value."""
        result = run_backtest(
            prices=synthetic_prices,
            weights=sample_weights,
            tickers=portfolio_tickers,
            portfolio_value=10000,
            benchmark_col="SPY",
        )
        # First value is (1 + 0) * 10000 = 10000
        assert result.portfolio_values[0] == pytest.approx(10000, rel=0.01)
