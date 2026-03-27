"""
Unified backtest engine for Black-Litterman portfolios.

Consolidates the backtest logic that was previously duplicated in:
  - core/report.py (_calculate_historical_performance)
  - utils/optimizer_wrapper.py (run_backtest)
  - utils/visualizations.py (create_historical_performance_chart — data calc)

All three consumers now call this module for calculations and handle
presentation (PDF, dict, Plotly chart) themselves.
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

from core.constants import (
    BENCHMARK_TICKER, RISK_FREE_RATE, TRADING_DAYS_PER_YEAR
)


@dataclass(frozen=True)
class BacktestMetrics:
    """Annualized performance metrics for a single series."""
    annualized_return: float      # as percentage (e.g. 12.5 for 12.5%)
    annualized_volatility: float  # as percentage
    sharpe_ratio: float
    max_drawdown: float           # as percentage (e.g. -15.2 for -15.2%)
    sortino_ratio: float
    calmar_ratio: float


@dataclass
class BacktestResult:
    """Complete result of a portfolio backtest vs benchmark."""
    # Time series data
    portfolio_cumulative_pct: List[float]   # cumulative % returns
    benchmark_cumulative_pct: List[float]   # cumulative % returns
    portfolio_values: List[float]           # dollar values
    benchmark_values: List[float]           # dollar values
    dates: List[str]                        # ISO date strings

    # Metrics
    portfolio_metrics: BacktestMetrics
    benchmark_metrics: BacktestMetrics

    # Metadata
    period_description: str

    # Convenience properties
    @property
    def ann_return(self) -> float:
        return self.portfolio_metrics.annualized_return

    @property
    def ann_volatility(self) -> float:
        return self.portfolio_metrics.annualized_volatility

    @property
    def sharpe(self) -> float:
        return self.portfolio_metrics.sharpe_ratio

    @property
    def benchmark_ann_return(self) -> float:
        return self.benchmark_metrics.annualized_return

    @property
    def benchmark_ann_volatility(self) -> float:
        return self.benchmark_metrics.annualized_volatility

    @property
    def benchmark_sharpe(self) -> float:
        return self.benchmark_metrics.sharpe_ratio

    def to_dict(self) -> dict:
        """Convert to dictionary format compatible with existing consumers."""
        return {
            'portfolio_values': self.portfolio_values,
            'spy_values': self.benchmark_values,
            'portfolio_pct': self.portfolio_cumulative_pct,
            'spy_pct': self.benchmark_cumulative_pct,
            'dates': self.dates,
            'return': self.portfolio_metrics.annualized_return,
            'volatility': self.portfolio_metrics.annualized_volatility,
            'sharpe': self.portfolio_metrics.sharpe_ratio,
            'max_drawdown': self.portfolio_metrics.max_drawdown,
            'sortino': self.portfolio_metrics.sortino_ratio,
            'calmar': self.portfolio_metrics.calmar_ratio,
            'spy_return': self.benchmark_metrics.annualized_return,
            'spy_volatility': self.benchmark_metrics.annualized_volatility,
            'spy_sharpe': self.benchmark_metrics.sharpe_ratio,
            'spy_max_drawdown': self.benchmark_metrics.max_drawdown,
            'spy_sortino': self.benchmark_metrics.sortino_ratio,
            'spy_calmar': self.benchmark_metrics.calmar_ratio,
            'period': self.period_description,
        }


def _calculate_annualized_metrics(
    daily_returns: pd.Series,
    cumulative_values: pd.Series,
    total_return: float,
    n_years: float
) -> BacktestMetrics:
    """Calculate annualized return, volatility, Sharpe, Sortino, Max Drawdown, and Calmar."""
    ann_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
    ann_vol = daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)

    # Canonical Sharpe: computed on daily excess returns, then annualized
    daily_rf = RISK_FREE_RATE / TRADING_DAYS_PER_YEAR
    excess_returns = daily_returns - daily_rf
    excess_std = excess_returns.std()
    sharpe = (excess_returns.mean() / excess_std * np.sqrt(TRADING_DAYS_PER_YEAR)
              if excess_std > 0 else 0)

    # Sortino Ratio (downside risk only)
    downside_returns = excess_returns[excess_returns < 0]
    downside_std = np.sqrt((downside_returns ** 2).mean())
    sortino = (excess_returns.mean() / downside_std * np.sqrt(TRADING_DAYS_PER_YEAR)
               if downside_std > 0 else 0)

    # Maximum Drawdown
    rolling_max = cumulative_values.cummax()
    drawdowns = (cumulative_values - rolling_max) / rolling_max
    max_dd = drawdowns.min()

    # Calmar Ratio
    calmar = ann_return / abs(max_dd) if abs(max_dd) > 0 else 0

    return BacktestMetrics(
        annualized_return=ann_return * 100,
        annualized_volatility=ann_vol * 100,
        sharpe_ratio=sharpe,
        max_drawdown=max_dd * 100,
        sortino_ratio=sortino,
        calmar_ratio=calmar
    )


def run_backtest(
    prices: pd.DataFrame,
    weights: Dict[str, float],
    tickers: List[str],
    portfolio_value: float,
    benchmark_col: str = BENCHMARK_TICKER,
    min_data_points: int = 100,
) -> Optional[BacktestResult]:
    """
    Run a historical backtest on a weighted portfolio vs a benchmark.

    This is the SINGLE SOURCE OF TRUTH for backtest calculations.
    All consumers (report.py, optimizer_wrapper.py, visualizations.py)
    should call this function instead of implementing their own.

    Args:
        prices: DataFrame with columns for each ticker AND the benchmark.
                Must already be cleaned (NaN rows dropped).
                Index must be DatetimeIndex.
        weights: {ticker: weight} dict from optimizer (e.g. {'MSFT': 0.4, 'AAPL': 0.6}).
        tickers: List of portfolio ticker symbols (NOT including benchmark).
        portfolio_value: Starting portfolio value in USD.
        benchmark_col: Column name for benchmark in prices DataFrame.
        min_data_points: Minimum number of rows required (default 100).

    Returns:
        BacktestResult dataclass, or None if insufficient data.
    """
    if len(prices) < min_data_points:
        return None

    # Validate that required columns exist
    missing_tickers = [t for t in tickers if t not in prices.columns]
    if missing_tickers:
        logger.warning("Missing tickers in price data: %s", missing_tickers)
        tickers = [t for t in tickers if t in prices.columns]

    if benchmark_col not in prices.columns:
        logger.error("Benchmark '%s' not found in price data", benchmark_col)
        return None

    if not tickers:
        logger.error("No valid tickers to backtest")
        return None

    # ── Portfolio daily returns (weighted sum) ──
    daily_returns = prices[tickers].pct_change().fillna(0)
    weights_array = np.array([weights.get(t, 0) for t in tickers])
    portfolio_returns = (daily_returns * weights_array).sum(axis=1)

    # ── Benchmark daily returns ──
    benchmark_returns = prices[benchmark_col].pct_change().fillna(0)

    # ── Cumulative dollar values ──
    portfolio_values = (1 + portfolio_returns).cumprod() * portfolio_value
    benchmark_values = (1 + benchmark_returns).cumprod() * portfolio_value

    # ── Cumulative percentage returns (for charts) ──
    portfolio_pct = ((1 + portfolio_returns).cumprod() - 1) * 100
    benchmark_pct = ((1 + benchmark_returns).cumprod() - 1) * 100

    # ── Annualized metrics ──
    n_years = len(prices) / TRADING_DAYS_PER_YEAR

    portfolio_total_return = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1
    benchmark_total_return = (benchmark_values.iloc[-1] / benchmark_values.iloc[0]) - 1

    portfolio_metrics = _calculate_annualized_metrics(
        portfolio_returns, portfolio_values, portfolio_total_return, n_years
    )
    benchmark_metrics = _calculate_annualized_metrics(
        benchmark_returns, benchmark_values, benchmark_total_return, n_years
    )

    # ── Build result ──
    start = prices.index[0].strftime('%Y-%m-%d')
    end = prices.index[-1].strftime('%Y-%m-%d')

    return BacktestResult(
        portfolio_cumulative_pct=portfolio_pct.tolist(),
        benchmark_cumulative_pct=benchmark_pct.tolist(),
        portfolio_values=portfolio_values.tolist(),
        benchmark_values=benchmark_values.tolist(),
        dates=[d.strftime('%Y-%m-%d') for d in prices.index],
        portfolio_metrics=portfolio_metrics,
        benchmark_metrics=benchmark_metrics,
        period_description=f"{start} to {end}",
    )


def download_and_run_backtest(
    tickers: List[str],
    weights: Dict[str, float],
    portfolio_value: float,
    years: int = 5,
    benchmark: str = BENCHMARK_TICKER,
) -> Optional[BacktestResult]:
    """
    Convenience function: downloads data and runs backtest.

    Use this when you don't already have price data available.
    When price data is already loaded (e.g. from optimization), prefer
    calling run_backtest() directly to avoid redundant downloads.

    Args:
        tickers: List of portfolio ticker symbols.
        weights: {ticker: weight} dict from optimizer.
        portfolio_value: Starting portfolio value in USD.
        years: Number of years of historical data (default 5).
        benchmark: Benchmark ticker symbol (default 'SPY').

    Returns:
        BacktestResult or None if download/calculation fails.
    """
    try:
        from core.data_provider import download_prices

        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365 + 30)

        all_tickers = list(set(tickers + [benchmark]))

        price_data = download_prices(
            all_tickers,
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
        )

        return run_backtest(
            prices=price_data,
            weights=weights,
            tickers=tickers,
            portfolio_value=portfolio_value,
            benchmark_col=benchmark,
        )

    except Exception as e:
        logger.error("Backtest download/calculation error: %s", e, exc_info=True)
        return None
