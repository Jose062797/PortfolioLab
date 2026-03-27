"""
Data provider for PortfolioLab platform.

Centralizes yfinance data downloading and parsing logic that was
previously duplicated in:
  - core/backtest.py (download_and_run_backtest)
  - utils/optimizer_wrapper.py (run_backtest fallback)
  - utils/visualizations.py (_prepare_price_data)

All consumers should use these functions instead of calling yfinance
directly and handling the single/multi-ticker parsing themselves.
"""

import logging
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)


def download_prices(
    tickers: List[str],
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: Optional[str] = None,
) -> pd.DataFrame:
    """
    Download closing prices from yfinance and return a clean DataFrame.

    Handles the single-ticker vs multi-ticker column structure differences
    that yfinance produces, returning a consistent DataFrame with one column
    per ticker.

    Args:
        tickers: List of ticker symbols (e.g., ['MSFT', 'AAPL', 'SPY']).
        start: Start date as 'YYYY-MM-DD' string (mutually exclusive with period).
        end: End date as 'YYYY-MM-DD' string (defaults to today if start is given).
        period: yfinance period string like "max", "5y" (mutually exclusive with start).

    Returns:
        DataFrame with DatetimeIndex and one column per ticker (NaN rows dropped).

    Raises:
        ValueError: If no data could be downloaded.
    """
    import yfinance as yf

    if start:
        raw = yf.download(tickers, start=start, end=end, progress=False)
    elif period:
        raw = yf.download(tickers, period=period, progress=False)
    else:
        raw = yf.download(tickers, period="max", progress=False)

    if raw.empty:
        raise ValueError(f"No data downloaded for {tickers}")

    return parse_yfinance_prices(raw, tickers)


def parse_yfinance_prices(raw_data: pd.DataFrame, tickers: List[str]) -> pd.DataFrame:
    """
    Extract closing prices from raw yfinance OHLCV data.

    Handles all the quirks of yfinance output:
    - Single ticker: flat columns like ['Open', 'High', 'Low', 'Close', 'Volume']
    - Multi ticker: MultiIndex columns like [('Close', 'AAPL'), ('Close', 'MSFT')]
    - Various column level names ('Price', None, etc.)

    Args:
        raw_data: Raw DataFrame from yf.download().
        tickers: List of ticker symbols that were requested.

    Returns:
        DataFrame with one column per ticker containing closing prices,
        with NaN rows dropped.

    Raises:
        ValueError: If closing prices cannot be extracted.
    """
    if raw_data.empty:
        raise ValueError("Empty DataFrame passed to parse_yfinance_prices")

    price_data = None

    if len(tickers) == 1:
        # Single ticker — flat columns
        if 'Close' in raw_data.columns:
            price_data = raw_data[['Close']].rename(columns={'Close': tickers[0]})
        elif 'Adj Close' in raw_data.columns:
            price_data = raw_data[['Adj Close']].rename(columns={'Adj Close': tickers[0]})
        else:
            # Might still have MultiIndex with single ticker
            try:
                price_data = raw_data.xs('Close', level='Price', axis=1)
            except (KeyError, TypeError):
                raise ValueError(f"Cannot extract closing prices for {tickers[0]}")
    else:
        # Multi ticker — try MultiIndex extraction
        for col_name in ('Close', 'Adj Close'):
            for level_name in ('Price', None):
                try:
                    if level_name is not None:
                        price_data = raw_data.xs(col_name, level=level_name, axis=1)
                    else:
                        price_data = raw_data[col_name]
                    break
                except (KeyError, TypeError):
                    continue
            if price_data is not None:
                break

        if price_data is None:
            raise ValueError("Cannot extract closing prices from yfinance data")

    if isinstance(price_data, pd.Series):
        price_data = price_data.to_frame()

    return price_data.dropna()


# ─────────────────────────────────────────────────────────────
# Stocks page — data functions (separate from Portfolio page)
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def download_ohlcv(ticker: str, period: str = "1y", interval: str = "1d",
                  auto_adjust: bool = True, prepost: bool = False,
                  start: str = None) -> pd.DataFrame:
    """
    Download full OHLCV data for a single ticker.

    Args:
        ticker: Single ticker symbol (e.g., 'MSFT', 'BTC-USD', 'QQQ').
        period: yfinance period string ('1d', '5d', '1mo', '3mo', '1y', etc.).
                Ignored when 'start' is provided.
        interval: yfinance interval string ('1m', '5m', '15m', '1d', etc.).
        start: Optional ISO date string (YYYY-MM-DD). When given, overrides
               'period' and downloads from this date to today.

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume.
        DatetimeIndex, NaN rows dropped.

    Raises:
        ValueError: If no data could be downloaded.
    """
    import yfinance as yf

    logger.info("Downloading OHLCV for %s (period=%s, start=%s, interval=%s)",
                ticker, period if not start else "n/a", start or "n/a", interval)
    use_prepost = prepost
    try:
        if start:
            raw = yf.download(ticker, start=start, interval=interval,
                              prepost=use_prepost, auto_adjust=auto_adjust, progress=False)
        else:
            raw = yf.download(ticker, period=period, interval=interval,
                              prepost=use_prepost, auto_adjust=auto_adjust, progress=False)
    except Exception as e:
        raise ValueError(f"Download failed for {ticker}: {e}")

    if raw is None or raw.empty:
        raise ValueError(f"No data downloaded for {ticker}")

    # Handle yfinance column structures (single ticker may have MultiIndex)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    required = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise ValueError(f"Missing columns {missing} for {ticker}")

    return raw[required].dropna()


@st.cache_data(ttl=300, show_spinner=False)
def get_asset_info(ticker: str) -> dict:
    """
    Fetch key fundamentals/info for a single ticker.

    Works for stocks, ETFs, crypto, indices — returns whatever is available.
    Never raises on missing fields (returns None for each).

    Strategy: fast_info (lightweight, rate-limit-resistant) is fetched first
    and used to fill any gaps left by the heavier .info call, which can be
    throttled on shared hosting environments (e.g. Streamlit Cloud).

    Args:
        ticker: Single ticker symbol.

    Returns:
        Dict with standardized keys. Missing fields are None.
    """
    import yfinance as yf

    logger.info("Fetching info for %s", ticker)
    stock = yf.Ticker(ticker)

    # ── fast_info: lightweight endpoint, works even under rate-limiting ────
    fast = {}
    try:
        fi = stock.fast_info
        fast = {
            'currentPrice':           getattr(fi, 'last_price', None),
            'previousClose':          getattr(fi, 'previous_close', None),
            'regularMarketOpen':      getattr(fi, 'open', None),
            'dayHigh':                getattr(fi, 'day_high', None),
            'dayLow':                 getattr(fi, 'day_low', None),
            'marketCap':              getattr(fi, 'market_cap', None),
            'volume':                 getattr(fi, 'last_volume', None),
            'averageVolume':          getattr(fi, 'three_month_average_volume', None),
            'fiftyTwoWeekHigh':       getattr(fi, 'year_high', None),
            'fiftyTwoWeekLow':        getattr(fi, 'year_low', None),
            'quoteType':              getattr(fi, 'quote_type', None),
            'currency':               getattr(fi, 'currency', None),
            'sharesOutstanding':      getattr(fi, 'shares', None),
        }
        fast = {k: v for k, v in fast.items() if v is not None}
    except Exception as e:
        logger.warning("fast_info failed for %s: %s", ticker, e)

    # ── analyst_price_targets: separate JSON endpoint, more reliable ──────
    try:
        apt = stock.analyst_price_targets
        if isinstance(apt, dict):
            for src_key, dst_key in [
                ('mean',   'targetMeanPrice'),
                ('low',    'targetLowPrice'),
                ('high',   'targetHighPrice'),
            ]:
                if apt.get(src_key) is not None and dst_key not in fast:
                    fast[dst_key] = apt[src_key]
    except Exception as e:
        logger.warning("analyst_price_targets failed for %s: %s", ticker, e)

    # ── full info: richer data, but may be rate-limited on cloud ──────────
    info = {}
    try:
        info = stock.info or {}
    except Exception as e:
        logger.warning("Failed to fetch info for %s: %s", ticker, e)

    # Merge: .info is primary; fast_info fills any None gaps
    def _get(key):
        v = info.get(key)
        if v is None:
            v = fast.get(key)
        return v

    return {
        # Identity
        'name': _get('shortName') or _get('longName') or ticker,
        'type': _get('quoteType'),  # EQUITY, ETF, CRYPTOCURRENCY, INDEX
        'sector': _get('sector'),
        'industry': _get('industry'),
        'currency': _get('currency'),
        'description': _get('longBusinessSummary'),
        # Trading data
        'price': _get('currentPrice') or _get('regularMarketPrice'),
        'previous_close': _get('previousClose') or _get('regularMarketPreviousClose'),
        'open_price': _get('regularMarketOpen') or _get('open'),
        'day_high': _get('dayHigh') or _get('regularMarketDayHigh'),
        'day_low': _get('dayLow') or _get('regularMarketDayLow'),
        'market_cap': _get('marketCap'),
        'volume': _get('volume') or _get('regularMarketVolume'),
        'avg_volume': _get('averageVolume'),
        'shares_outstanding': _get('sharesOutstanding'),
        # 52-week range
        'fifty_two_week_high': _get('fiftyTwoWeekHigh'),
        'fifty_two_week_low': _get('fiftyTwoWeekLow'),
        # Valuation
        'pe_ratio': _get('trailingPE'),
        'forward_pe': _get('forwardPE'),
        'peg_ratio': _get('pegRatio') or _get('trailingPegRatio'),
        'eps': _get('trailingEps'),
        'book_value': _get('bookValue'),
        'price_to_book': _get('priceToBook'),
        'price_to_sales': _get('priceToSalesTrailing12Months'),
        'enterprise_value': _get('enterpriseValue'),
        'ev_to_ebitda': _get('enterpriseToEbitda'),
        # Profitability
        'revenue': _get('totalRevenue'),
        'net_income': _get('netIncomeToCommon'),
        'ebitda': _get('ebitda'),
        'profit_margin': _get('profitMargins') or _get('profitMargin'),
        'gross_margins': _get('grossMargins'),
        'operating_margins': _get('operatingMargins'),
        'return_on_equity': _get('returnOnEquity'),
        'return_on_assets': _get('returnOnAssets'),
        # Dividends
        'dividend_yield': _get('trailingAnnualDividendYield') or _get('dividendYield'),
        'dividend_rate': _get('dividendRate'),
        'ex_dividend_date': _get('exDividendDate'),
        # Analyst consensus
        'target_mean_price': _get('targetMeanPrice'),
        'target_high_price': _get('targetHighPrice'),
        'target_low_price': _get('targetLowPrice'),
        'recommendation': _get('recommendationKey'),
        'num_analyst_opinions': _get('numberOfAnalystOpinions'),
        # Risk
        'beta': _get('beta'),
        # ── ETF-specific ──
        'nav_price': _get('navPrice'),
        'expense_ratio': ((_get('netExpenseRatio') or _get('annualReportExpenseRatio') or _get('totalExpenseRatio')) / 100.0) 
                          if (_get('netExpenseRatio') or _get('annualReportExpenseRatio') or _get('totalExpenseRatio')) is not None else None,
        'net_assets': _get('totalAssets'),
        'ytd_return': (_get('ytdReturn') / 100.0) if _get('ytdReturn') is not None else None,
        'fund_inception_date': _get('fundInceptionDate'),
        'fund_family': _get('fundFamily'),
        'yield_pct': _get('yield'),
        # ── Crypto-specific ──
        'circulating_supply': _get('circulatingSupply'),
        'max_supply': _get('maxSupply') or _get('totalSupply'),
        'volume_24h': _get('volume24Hr'),
        'start_date': _get('startDate'),
        # Bid/Ask (available during market hours)
        'bid': _get('bid'),
        'bid_size': _get('bidSize'),
        'ask': _get('ask'),
        'ask_size': _get('askSize'),
        # Next earnings date (Unix timestamp)
        'next_earnings_date': _get('earningsTimestamp'),
    }
@st.cache_data(ttl=3600, show_spinner=False)
def get_quarterly_financials(ticker: str) -> pd.DataFrame:
    """
    Fetch quarterly revenue and net income for a ticker.

    Returns:
        DataFrame with DatetimeIndex (quarter dates, ascending) and columns
        'revenue' and/or 'net_income'. Empty DataFrame if unavailable.
    """
    import yfinance as yf

    logger.info("Fetching quarterly financials for %s", ticker)
    try:
        stock = yf.Ticker(ticker)
        stmt = stock.quarterly_income_stmt
        if stmt is None or stmt.empty:
            return pd.DataFrame()

        # Flexible row matching — yfinance row names vary by company/version
        revenue_row = None
        net_income_row = None
        for row in stmt.index:
            row_str = str(row).lower()
            if revenue_row is None and 'total revenue' in row_str:
                revenue_row = row
            if net_income_row is None and 'net income' in row_str \
                    and 'non' not in row_str and 'minority' not in row_str:
                net_income_row = row

        data = {}
        if revenue_row is not None:
            data['revenue'] = stmt.loc[revenue_row]
        if net_income_row is not None:
            data['net_income'] = stmt.loc[net_income_row]

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        # Normalize index to timezone-naive and sort chronologically
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df = df.sort_index(ascending=True)
        return df
    except Exception as e:
        logger.warning("Failed to fetch quarterly financials for %s: %s", ticker, e)
        return pd.DataFrame()
