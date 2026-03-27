"""
Optimizer Wrapper for Streamlit Integration

This module wraps the core Black-Litterman optimizer (core/opt.py)
to provide a clean, Streamlit-friendly interface with consistent
error handling and result formatting.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
import pandas as pd
import streamlit as st

from core.opt_engine import (
    download_data,
    calculate_prior,
    run_black_litterman,
    calculate_markowitz_inputs,
    calculate_efficient_frontier,
    optimize_portfolio,
    calculate_allocation
)
from core.constants import (
    RISK_FREE_RATE,
    MIN_TICKERS,
    MAX_TICKERS,
    MIN_PORTFOLIO_VALUE,
    MAX_PORTFOLIO_VALUE,
    MIN_WEIGHT_THRESHOLD,
    DEFAULT_PORTFOLIO_VALUE,
    BENCHMARK_TICKER,
    TRADING_DAYS_PER_YEAR
)

logger = logging.getLogger(__name__)


def _download_data_from_tuples(tickers_tuple, date_range_tuple):
    """
    Wrapper for download_data that accepts tuples (from Streamlit UI).
    Always downloads fresh data from yfinance, matching notebook behavior.
    """
    tickers = list(tickers_tuple)
    date_range = list(date_range_tuple) if date_range_tuple else None
    return download_data(tickers, date_range)


def validate_inputs(
    tickers: List[str],
    portfolio_value: float,
    date_range: Optional[Tuple] = None,
    views: Optional[Dict] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate optimization inputs.

    Args:
        tickers: List of ticker symbols
        portfolio_value: Portfolio value in USD
        date_range: Optional (start_date, end_date) tuple
        views: Optional investment views dict

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate tickers
    if not tickers or len(tickers) < MIN_TICKERS:
        return False, f"Need at least {MIN_TICKERS} tickers"

    if len(tickers) > MAX_TICKERS:
        return False, f"Maximum {MAX_TICKERS} tickers allowed"

    if len(tickers) != len(set(tickers)):
        return False, "Duplicate tickers found"

    # Validate portfolio value
    if portfolio_value < MIN_PORTFOLIO_VALUE:
        return False, f"Portfolio value must be at least ${MIN_PORTFOLIO_VALUE}"

    if portfolio_value > MAX_PORTFOLIO_VALUE:
        return False, f"Portfolio value cannot exceed ${MAX_PORTFOLIO_VALUE:,.0f}"

    # Validate date range if provided
    if date_range:
        try:
            start, end = date_range
            if start >= end:
                return False, "Start date must be before end date"
        except Exception as e:
            return False, f"Invalid date range: {e}"

    # Validate views if provided
    if views:
        for ticker, view_data in views.items():
            if ticker not in tickers:
                return False, f"View provided for ticker '{ticker}' not in ticker list"

            if 'expected' not in view_data:
                return False, f"View for {ticker} missing 'expected' return"

            # Basic sanity checks
            expected = view_data['expected']
            if abs(expected) > 2.0:  # 200% sanity check
                return False, f"View for {ticker} seems unrealistic: {expected*100:.0f}%"

    return True, None


def run_optimization(
    tickers: List[str],
    portfolio_value: float,
    date_range: Optional[Tuple] = None,
    views: Optional[Dict[str, Dict[str, float]]] = None,
    progress_callback: Optional[callable] = None,
    model_type: str = "Black-Litterman",
    obj_function: str = "Max Sharpe",
    target_volatility: float = 0.20,
    target_return: float = 0.15,
    l2_gamma: float = 0.0
) -> Dict[str, Any]:
    """
    Execute portfolio optimization (Markowitz or Black-Litterman).

    Args:
        tickers: List of ticker symbols (e.g., ['MSFT', 'AMZN', 'GOOGL'])
        portfolio_value: Total portfolio value in USD
        date_range: Optional (start_date, end_date) tuple for historical data
        views: Optional investment views dict (BL only)
               Format: {
                   'MSFT': {'expected': 0.15, 'lower': 0.10, 'upper': 0.20},
                   'AMZN': {'expected': 0.12, 'lower': 0.08, 'upper': 0.16}
               }
        progress_callback: Optional callback function for progress updates
        model_type: 'Black-Litterman' or 'Markowitz'
        obj_function: 'Min Variance', 'Max Sharpe', 'Maximise Return for a Given Risk',
                      or 'Minimise Risk for a Given Return'
        target_volatility: Target volatility for 'Maximise Return for a Given Risk' (default 0.20)
        target_return: Target return for 'Minimise Risk for a Given Return' (default 0.15)
        l2_gamma: L2 regularization strength (0.0=none/default, higher=more diversified)

    Returns:
        Dictionary with 'success', 'metrics', 'weights', 'allocation', etc.
    """
    def update_progress(message: str):
        """Helper to call progress callback if provided."""
        if progress_callback:
            progress_callback(message)

    try:
        # Validate inputs
        update_progress("Validating inputs...")
        is_valid, error_msg = validate_inputs(tickers, portfolio_value, date_range, views)
        if not is_valid:
            return {
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }

        # Convert views format if provided
        viewdict = None
        intervals = None
        if views:
            viewdict = {}
            intervals = {}
            for ticker, view_data in views.items():
                viewdict[ticker] = view_data['expected']
                intervals[ticker] = (view_data.get('lower', 0), view_data.get('upper', 0))

        # Step 1: Download fresh data (no cache — matches notebook behavior)
        update_progress(f"Downloading data for {len(tickers)} tickers...")
        tickers_tuple = tuple(sorted(tickers))
        date_range_tuple = tuple(date_range) if date_range else None
        prices, market_prices, mcaps = _download_data_from_tuples(tickers_tuple, date_range_tuple)

        S = None
        delta = None
        market_prior = None

        if model_type == "Markowitz":
            update_progress("Calculating standard Markowitz inputs...")
            spy_aligned = market_prices.loc[prices.index[0]:prices.index[-1]]
            prices_clean = prices.copy()

            # CAPM needs market prices for beta calculation, but SPY must NOT
            # be included in `prices_clean` or it becomes an allocatable asset.
            mu, S_bl = calculate_markowitz_inputs(prices_clean, market_prices=spy_aligned)
            ret_bl = mu

            # Now add SPY back safely for downstream tracking/plotting
            prices_clean[BENCHMARK_TICKER] = spy_aligned
        else:
            # Step 2: Calculate market prior (pairwise covariance, returns cleaned prices for downstream)
            update_progress("Calculating market equilibrium...")
            S, delta, market_prior, prices_clean2 = calculate_prior(prices, market_prices, mcaps)
            # Ensure we use identically cleaned
            prices_clean = prices_clean2
            
            # Step 3: Run Black-Litterman model
            if viewdict:
                update_progress(f"Incorporating {len(viewdict)} investment views...")
            else:
                update_progress("Using market equilibrium (no custom views)...")

            bl, ret_bl, S_bl = run_black_litterman(S, delta, mcaps, market_prior, viewdict, intervals)

        # Step 4: Optimize portfolio
        update_progress(f"Optimizing portfolio weights ({obj_function})...")
        weights, performance_metrics = optimize_portfolio(
            ret_bl, S_bl, 
            obj_function=obj_function, 
            target_volatility=target_volatility, 
            target_return=target_return,
            l2_gamma=l2_gamma
        )

        ef_data = None
        if model_type == "Markowitz":
            update_progress("Calculating efficient frontier...")
            ef_data = calculate_efficient_frontier(ret_bl, S_bl)

        # Step 5: Calculate discrete allocation
        update_progress("Calculating share allocation...")
        # Exclude SPY from prices for allocation (only need portfolio tickers)
        prices_for_allocation = prices_clean[[t for t in tickers if t in prices_clean.columns]]
        allocation, leftover = calculate_allocation(weights, prices_for_allocation, portfolio_value)

        # Extract date ranges:
        # - Full data range: used for covariance estimation (pairwise, max data)
        # - Common data range: from dropna, used for backtest/allocation
        full_data_start = prices.index[0].strftime('%Y-%m-%d')
        full_data_end = prices.index[-1].strftime('%Y-%m-%d')
        analysis_start = prices_clean.index[0].strftime('%Y-%m-%d')
        analysis_end = prices_clean.index[-1].strftime('%Y-%m-%d')

        # Build result dictionary
        result = {
            'success': True,
            'metrics': {
                'return': performance_metrics['expected_return'],
                'volatility': performance_metrics['volatility'],
                'sharpe': performance_metrics['sharpe_ratio']
            },
            'weights': weights,
            'allocation': allocation,
            'leftover': float(leftover),
            'market_prior': market_prior.to_dict() if market_prior is not None else {},
            'posterior': ret_bl.to_dict() if hasattr(ret_bl, 'to_dict') else {},
            'tickers': tickers,
            'portfolio_value': float(portfolio_value),
            'timestamp': datetime.now().isoformat(),
            'date_range': (analysis_start, analysis_end),
            'full_data_range': (full_data_start, full_data_end),
            'viewdict': viewdict if viewdict else {},
            'views_detail': views if views else {},
            'model_type': model_type,
            'covariance_matrix': S_bl.tolist() if (S_bl is not None and hasattr(S_bl, 'tolist')) else (S_bl.values.tolist() if (S_bl is not None and hasattr(S_bl, 'values')) else None),
            'risk_free_rate': RISK_FREE_RATE,
            'benchmark': BENCHMARK_TICKER,
            'obj_function': obj_function,
            'ef_data': ef_data,
            # Include cleaned price data for consistent backtesting
            'prices_clean': prices_clean.to_dict('index')  # Convert to dict for JSON serialization
        }

        update_progress("Optimization complete!")
        return result

    except Exception as e:
        error_msg = str(e)
        logger.error("Optimization error: %s", error_msg)

        return {
            'success': False,
            'error': error_msg,
            'timestamp': datetime.now().isoformat(),
            'tickers': tickers,
            'portfolio_value': portfolio_value
        }


def run_backtest(
    result: Dict[str, Any],
    backtest_years: int = None,
    date_range: Tuple[str, str] = None
) -> Optional[Dict[str, Any]]:
    """
    Run historical backtest on optimized portfolio.

    Delegates all calculations to core.backtest (single source of truth).
    This function handles data preparation (reuse from optimization or download).

    Args:
        result: Optimization result dictionary
        backtest_years: Number of years to backtest (deprecated, use date_range instead)
        date_range: Tuple of (start_date, end_date) as strings in 'YYYY-MM-DD' format
                   If provided, this takes precedence over backtest_years

    Returns:
        Dictionary with backtest results, or None if failed.
    """
    from core.backtest import run_backtest as _core_backtest

    try:
        import yfinance as yf
        import numpy as np
        from datetime import datetime, timedelta

        tickers = result.get('tickers', [])
        weights = result.get('weights', {})
        portfolio_value = result.get('portfolio_value', 20000)

        if not tickers or not weights:
            return None

        # Option A: Reuse cleaned price data from optimization if available
        prices_clean_dict = result.get('prices_clean', None)

        if prices_clean_dict:
            price_data = pd.DataFrame.from_dict(prices_clean_dict, orient='index')
            price_data.index = pd.to_datetime(price_data.index)

            if BENCHMARK_TICKER not in price_data.columns:
                print(f"[WARNING] {BENCHMARK_TICKER} not found in prices_clean, downloading...")
                spy_data = yf.download(
                    BENCHMARK_TICKER,
                    start=price_data.index[0].strftime('%Y-%m-%d'),
                    end=price_data.index[-1].strftime('%Y-%m-%d'),
                    progress=False
                )
                if 'Close' in spy_data.columns:
                    price_data[BENCHMARK_TICKER] = spy_data['Close']
                else:
                    price_data[BENCHMARK_TICKER] = spy_data['Adj Close']
                price_data = price_data.dropna()

            print(f"[Backtest] Reusing cleaned data from optimization: {len(price_data)} days")
        else:
            # Fallback: Download data if not available
            from core.data_provider import download_prices

            print("[Backtest] Downloading data (prices_clean not available in result)")

            if date_range:
                start_date_str, end_date_str = date_range
            elif backtest_years:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=backtest_years * 365 + 30)
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = end_date.strftime('%Y-%m-%d')
            else:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=10 * 365 + 30)
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = end_date.strftime('%Y-%m-%d')

            all_tickers = tickers + [BENCHMARK_TICKER]
            price_data = download_prices(
                all_tickers,
                start=start_date_str,
                end=end_date_str,
            )

        # Delegate to unified backtest engine
        bt_result = _core_backtest(
            prices=price_data,
            weights=weights,
            tickers=tickers,
            portfolio_value=portfolio_value,
            benchmark_col=BENCHMARK_TICKER,
        )

        return bt_result.to_dict() if bt_result else None

    except Exception as e:
        print(f"Backtest error: {e}")
        import traceback
        traceback.print_exc()
        return None

