"""
Black-Litterman Portfolio Optimization Engine

Pure computation module — no CLI I/O, no matplotlib plots.
All functions accept data and return results.
Diagnostics go through the logging module (not print).

Consumers:
  - core/opt_cli.py (CLI interface)
  - utils/optimizer_wrapper.py (Streamlit bridge)
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from core.constants import (
    RISK_FREE_RATE, MIN_DATA_POINTS,
    MIN_WEIGHT_THRESHOLD, BENCHMARK_TICKER,
    OptimizationError, DataDownloadError, InsufficientDataError
)

logger = logging.getLogger(__name__)

# Lazy-import heavy libraries so import-time stays fast
_yf = None
_pypfopt = None


def _get_yf():
    global _yf
    if _yf is None:
        import yfinance as yf
        _yf = yf
    return _yf


def _get_pypfopt():
    global _pypfopt
    if _pypfopt is None:
        from pypfopt import (
            BlackLittermanModel, risk_models, black_litterman,
            EfficientFrontier, objective_functions, DiscreteAllocation,
            expected_returns
        )
        _pypfopt = type('pypfopt', (), {
            'BlackLittermanModel': BlackLittermanModel,
            'risk_models': risk_models,
            'black_litterman': black_litterman,
            'EfficientFrontier': EfficientFrontier,
            'objective_functions': objective_functions,
            'DiscreteAllocation': DiscreteAllocation,
            'expected_returns': expected_returns,
        })
    return _pypfopt


def download_data(tickers, date_range):
    """Download price data with retry logic and robust error handling."""
    import time

    yf = _get_yf()
    max_retries = 3
    retry_delays = [0, 2, 5]

    logger.info("Downloading data for %d tickers", len(tickers))

    # Download price data with retries
    prices = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                logger.info("Retrying... (attempt %d/%d)", attempt + 1, max_retries)
                time.sleep(retry_delays[attempt])

            logger.info("Downloading price data...")

            if date_range:
                start, end = date_range
                if isinstance(end, str):
                    end_dt = datetime.strptime(end, '%Y-%m-%d')
                else:
                    end_dt = end
                end_adjusted = end_dt + timedelta(days=1)
                ohlc = yf.download(tickers, start=start, end=end_adjusted, progress=False)
            else:
                ohlc = yf.download(tickers, period="max", progress=False)

            if len(tickers) == 1:
                if ohlc.empty:
                    raise ValueError(f"No data downloaded for {tickers[0]}")
                prices = ohlc["Close"].to_frame()
                prices.columns = tickers
            else:
                if "Close" not in ohlc.columns:
                    raise ValueError("No price data downloaded")
                prices = ohlc["Close"]

            if len(prices) < MIN_DATA_POINTS:
                raise InsufficientDataError(f"Insufficient data: only {len(prices)} days (need at least {MIN_DATA_POINTS})")

            logger.info("Downloaded %d days of data (%s to %s)",
                        len(prices), prices.index[0].date(), prices.index[-1].date())
            break

        except Exception as e:
            if attempt == max_retries - 1:
                logger.error("Data download failed after %d attempts: %s", max_retries, e)
                raise
            else:
                logger.warning("Download failed: %s", e)

    # Download market data (SPY) with retries
    market_prices = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                logger.info("Retrying market data... (attempt %d/%d)", attempt + 1, max_retries)
                time.sleep(retry_delays[attempt])

            logger.info("Downloading market data...")
            if date_range:
                market_data = yf.download(BENCHMARK_TICKER, start=start, end=end_adjusted, progress=False)
            else:
                market_data = yf.download(BENCHMARK_TICKER, period="max", progress=False)

            if market_data.empty:
                raise ValueError(f"Could not download {BENCHMARK_TICKER} market data")

            market_prices = market_data["Close"]
            logger.info("Market data downloaded")
            break

        except Exception as e:
            if attempt == max_retries - 1:
                logger.error("Failed to download %s benchmark after %d attempts: %s",
                             BENCHMARK_TICKER, max_retries, e)
                raise
            else:
                logger.warning("Market data download failed: %s", e)

    return prices, market_prices


def download_market_caps(tickers: list) -> dict:
    """
    Download market sizes for a list of tickers for use as BL market weights.

    Field priority per asset type:
      - ETFs/funds: totalAssets (AUM) — marketCap is inconsistent or missing
      - Stocks:     marketCap — standard BL assumption

    Uses totalAssets → marketCap fallback chain so ETFs and stocks are handled
    consistently with a single call per ticker.

    Raises DataDownloadError if a ticker's size cannot be fetched after all
    retries — no silent fallbacks. Only called for Black-Litterman, where
    incorrect market weights directly corrupt the market-implied prior returns.

    Retries with increasing delays to handle Yahoo Finance rate-limiting that
    commonly occurs immediately after a price data download.

    Args:
        tickers: List of ticker symbols.

    Returns:
        Dict mapping ticker → market size (float, in USD).

    Raises:
        DataDownloadError: If any ticker's market size is unavailable after retries.
    """
    import time
    yf = _get_yf()
    mcaps = {}
    max_retries = 3
    # Inter-ticker pause: space out individual .info calls to avoid triggering
    # Yahoo Finance's per-IP rate limit on /v10/quoteSummary/.
    # The original [1, 4, 8] delays worked because attempt-0 sleep(1) naturally
    # paced each ticker 1s apart. Removing that spacing caused burst failures.
    inter_ticker_pause = 1.5  # seconds between each ticker's first request
    # Retry delays for subsequent attempts after a failure (not applied on attempt 0)
    retry_delays = [0, 8, 20]

    logger.info("Downloading market caps for %d tickers...", len(tickers))
    # Brief pause so the price-download rate limit window has time to clear
    # before we start hitting the (stricter) quoteSummary endpoint.
    time.sleep(3)

    for ticker in tickers:
        cap = None
        last_error = None

        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    # Natural pacing between tickers on first attempt
                    time.sleep(inter_ticker_pause)
                else:
                    logger.info("Retrying market cap for %s (attempt %d/%d)...",
                                ticker, attempt + 1, max_retries)
                    time.sleep(retry_delays[attempt])
                info = yf.Ticker(ticker).info
                # totalAssets (AUM) first — consistent for ETFs/funds.
                # marketCap fallback for individual stocks.
                cap = info.get("totalAssets") or info.get("marketCap")
                if cap:
                    logger.debug("  %s: $%,.0f (field=%s)", ticker, cap,
                                 "totalAssets" if info.get("totalAssets") else "marketCap")
                    break
                last_error = f"neither totalAssets nor marketCap available for '{ticker}'"
            except Exception as e:
                last_error = str(e)
                logger.warning("Market cap attempt %d failed for %s: %s",
                               attempt + 1, ticker, e)

        if not cap:
            raise DataDownloadError(
                f"Could not fetch market size for '{ticker}' after {max_retries} attempts. "
                f"Yahoo Finance may be rate-limiting — please try again in a moment. "
                f"(Last error: {last_error})"
            )

        mcaps[ticker] = cap
        logger.debug("  %s: $%,.0f", ticker, cap)

    return mcaps


def calculate_prior(prices, market_prices, mcaps):
    """Calculate market-implied prior returns."""
    pp = _get_pypfopt()

    logger.info("Calculating market prior (%d days of price data)", len(prices))

    try:
        for ticker in prices.columns:
            valid = prices[ticker].notna().sum()
            logger.debug("  %s: %d valid observations", ticker, valid)

        # Let PyPortfolioOpt handle NaNs internally like the notebook
        S = pp.risk_models.CovarianceShrinkage(prices).ledoit_wolf()
        logger.info("Covariance matrix calculated (Ledoit-Wolf shrinkage)")

        delta = pp.black_litterman.market_implied_risk_aversion(market_prices)
        logger.info("Risk aversion: %.2f", delta)

        market_prior = pp.black_litterman.market_implied_prior_returns(mcaps, delta, S)

        for ticker, ret in market_prior.items():
            logger.debug("  Prior %s: %.2f%%", ticker, ret * 100)

        # Use prices consistently like the notebook
        spy_aligned = market_prices.loc[prices.index[0]:prices.index[-1]]
        prices_with_spy = prices.copy()
        prices_with_spy[BENCHMARK_TICKER] = spy_aligned

        return S, delta, market_prior, prices_with_spy

    except Exception as e:
        logger.error("Error calculating prior: %s", e)
        raise OptimizationError(f"Failed to calculate market prior: {e}") from e


def run_black_litterman(S, delta, mcaps, market_prior, viewdict, intervals):
    """Run Black-Litterman model."""
    pp = _get_pypfopt()

    try:
        if viewdict is None or len(viewdict) == 0:
            logger.info("Using market equilibrium (no views)")
            ret_bl = market_prior
            S_bl = S
            bl = None
        else:
            logger.info("Incorporating %d view(s)", len(viewdict))

            variances = []
            for ticker in viewdict.keys():
                lower, upper = intervals[ticker]
                sigma = (upper - lower) / 2
                variance = sigma ** 2
                variances.append(variance)

            omega = np.diag(variances)

            bl = pp.BlackLittermanModel(
                S,
                pi="market",
                market_caps=mcaps,
                risk_aversion=delta,
                absolute_views=viewdict,
                omega=omega
            )

            ret_bl = bl.bl_returns()
            S_bl = bl.bl_cov()

        for ticker, ret in ret_bl.items():
            logger.debug("  Posterior %s: %.2f%%", ticker, ret * 100)

        return bl, ret_bl, S_bl

    except Exception as e:
        logger.error("Black-Litterman model failed: %s", e)
        raise OptimizationError(f"Black-Litterman model failed: {e}") from e


def calculate_markowitz_inputs(
    prices: pd.DataFrame,
    market_prices: pd.DataFrame = None,
) -> tuple[pd.Series, pd.DataFrame]:
    """
    Calculate standard Markowitz Mean-Variance Optimization inputs.

    Args:
        prices: Cleaned historical prices dataframe (portfolio tickers only)
        market_prices: Optional market benchmark prices (e.g. SPY) for CAPM beta

    Returns:
        tuple containing:
            - mu (pd.Series): Expected CAPM returns
            - S (pd.DataFrame): Covariance matrix using Ledoit-Wolf shrinkage
    """
    pypfopt = _get_pypfopt()

    logger.debug(f"[Engine] Calculating Markowitz inputs for {prices.shape[1]} assets over {prices.shape[0]} days")

    # Use CAPM returns as recommended by the PyPortfolioOpt cookbook
    # (2-Mean-Variance-Optimisation.ipynb). CAPM returns are more stable
    # than simple mean historical returns for portfolio optimization.
    try:
        mu = pypfopt.expected_returns.capm_return(prices, market_prices=market_prices)
        S = pypfopt.risk_models.CovarianceShrinkage(prices).ledoit_wolf()
        logger.debug("[Engine] Markowitz inputs calculated successfully.")
        return mu, S
    except Exception as e:
        logger.error(f"[Engine] Error calculating Markowitz inputs: {str(e)}")
        raise OptimizationError(f"Failed to calculate Markowitz inputs: {str(e)}")

def calculate_efficient_frontier(mu, S, points=100):
    """
    Calculate the efficient frontier using the EfficientFrontier class.
    Returns lists of returns and risks forming the frontier, as well as optimal portfolio and asset points.
    """
    pp = _get_pypfopt()
    logger.info("Computing Efficient Frontier values using scipy...")
    
    try:
        # 1. Optimal tangency portfolio
        ef_sharpe = pp.EfficientFrontier(mu, S)
        ef_sharpe.max_sharpe()
        optimal_ret, optimal_risk, sharpe_max = ef_sharpe.portfolio_performance()
        
        # 2. Min volatility portfolio
        ef_min = pp.EfficientFrontier(mu, S)
        ef_min.min_volatility()
        min_ret, min_vol, _ = ef_min.portfolio_performance()
        
        max_ret = mu.max()
        
        # Generate target returns
        target_returns = np.linspace(min_ret, max_ret, points)
        mus = []
        sigmas = []
        
        for target_ret in target_returns:
            try:
                ef = pp.EfficientFrontier(mu, S)
                ef.efficient_return(target_return=target_ret)
                ret, vol, _ = ef.portfolio_performance()
                mus.append(ret)
                sigmas.append(vol)
            except Exception as e:
                logger.debug("Skipping frontier point at target_ret=%.4f: %s", target_ret, e)
        
        # Extract individual asset expected returns and volatilities
        asset_mu = mu.to_dict()
        asset_sigma = {ticker: np.sqrt(S.loc[ticker, ticker]) for ticker in mu.index}
        
        return {
            'mus': mus,
            'sigmas': sigmas,
            'optimal_ret': optimal_ret,
            'optimal_risk': optimal_risk,
            'sharpe_max': sharpe_max,
            'min_vol_ret': min_ret,
            'min_vol_risk': min_vol,
            'asset_mu': asset_mu,
            'asset_sigma': asset_sigma
        }
    except Exception as e:
        logger.error("Failed to compute Efficient Frontier: %s", e)
        return None

def optimize_portfolio(ret_bl, S_bl, obj_function="Max Sharpe", target_volatility=0.20, target_return=0.15, l2_gamma=0.0):
    """Optimize portfolio weights."""
    pp = _get_pypfopt()

    logger.info("Optimizing portfolio weights (Obj: %s, L2 Gamma: %.2f)...", obj_function, l2_gamma)

    try:
        ef = pp.EfficientFrontier(ret_bl, S_bl)
        
        # Apply L2 Regularization (skip when gamma=0 to avoid unnecessary computation)
        if l2_gamma > 0:
            ef.add_objective(pp.objective_functions.L2_reg, gamma=l2_gamma)
        
        # Select Optimization Objective
        if obj_function == "Min Variance":
            ef.min_volatility()
        elif obj_function == "Max Sharpe":
            ef.max_sharpe()
        elif obj_function == "Maximise Return for a Given Risk":
            ef.efficient_risk(target_volatility=target_volatility)
        elif obj_function == "Minimise Risk for a Given Return":
            ef.efficient_return(target_return=target_return)
        else:
            # Default fallback
            ef.max_sharpe()
            
        weights = ef.clean_weights()

        for ticker, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            if weight > MIN_WEIGHT_THRESHOLD:
                logger.debug("  %s: %.1f%%", ticker, weight * 100)

        ret, vol, sharpe = ef.portfolio_performance(verbose=False, risk_free_rate=RISK_FREE_RATE)
        logger.info("Optimization complete: return=%.1f%%, vol=%.1f%%, sharpe=%.2f",
                     ret * 100, vol * 100, sharpe)

        performance_metrics = {
            'expected_return': ret,
            'volatility': vol,
            'sharpe_ratio': sharpe
        }

        return weights, performance_metrics

    except Exception as e:
        logger.error("Portfolio optimization failed: %s", e)
        raise OptimizationError(f"Portfolio optimization failed: {e}") from e


def calculate_allocation(weights, prices, portfolio_value):
    """Calculate discrete share allocation with fractional display."""
    pp = _get_pypfopt()

    logger.info("Calculating discrete allocation for $%.0f", portfolio_value)

    try:
        # Forward-fill then take last row so every ticker has a valid price
        # even if the most recent date has NaN (partial data for today).
        # Matches notebook intent: prices.iloc[-1] on already-clean data.
        latest_prices = prices.ffill().iloc[-1]
        latest_prices = latest_prices[list(weights.keys())]

        for ticker in weights.keys():
            if weights[ticker] > MIN_WEIGHT_THRESHOLD:
                price = latest_prices[ticker]
                target_value = weights[ticker] * portfolio_value
                fractional_shares = target_value / price
                logger.debug("  %s: $%.2f/share (target: %.2f shares = $%,.2f)",
                             ticker, price, fractional_shares, target_value)

        da = pp.DiscreteAllocation(weights, latest_prices, total_portfolio_value=portfolio_value)

        # lp_portfolio() requires the ECOS_BB solver (mixed-integer LP).
        # On environments where ECOS_BB is not installed (e.g. Streamlit Cloud),
        # fall back to greedy_portfolio() which has no solver dependency.
        try:
            allocation, leftover = da.lp_portfolio()
            if not allocation or len(allocation) == 0:
                raise ValueError("LP returned empty allocation")
        except Exception as lp_err:
            logger.warning("LP allocation failed (%s), falling back to greedy method.", lp_err)
            allocation, leftover = da.greedy_portfolio()

        if allocation and len(allocation) > 0:
            total_invested = sum(allocation[t] * latest_prices[t] for t in allocation)
            logger.info("Allocated %d positions, $%.2f invested, $%.2f remaining",
                        len(allocation), total_invested, leftover)
        else:
            logger.warning("No shares could be allocated (portfolio too small for share prices)")
            leftover = portfolio_value

        return allocation, leftover

    except Exception as e:
        logger.error("Error calculating allocation: %s", e, exc_info=True)
        raise OptimizationError(f"Share allocation failed: {e}") from e
