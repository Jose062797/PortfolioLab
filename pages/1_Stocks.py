"""
Stocks – Yahoo Finance-inspired adaptive asset explorer.
"""

import sys
import os
import re
import html
import math
import logging
import datetime as _dt

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# ── Paths ────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

st.set_page_config(
    page_title="Stocks · PortfolioLab",
    page_icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "favicon.png"),
    layout="wide",
)

from utils.styles import inject_critical_css, inject_styles, render_navbar  # noqa: E402
inject_critical_css()
inject_styles()
render_navbar(active_page="stocks")

from core.data_provider import (  # noqa: E402
    download_ohlcv, get_asset_info, get_quarterly_financials,
)
from utils.visualizations import apply_brand_layout, create_price_chart  # noqa: E402
from utils.text import escape_markdown, fmt_price  # noqa: E402
from core.constants import TICKER_PATTERN  # noqa: E402

logger = logging.getLogger(__name__)


# ── Cached data layer (audit D6.1) ──
# Yahoo data is already ~15 min delayed for many exchanges, so a short TTL
# loses no real freshness while removing repeat downloads (and rate-limit
# exposure) when switching periods or revisiting a ticker. Applies ONLY to
# this exploration page — the Portfolio optimizer always downloads fresh
# by design (notebook fidelity). The caches are shared by every visitor, so
# each also has a size cap (audit B5-06): a full daily history is about
# 0.5 MB, and only the TTL used to bound them.

@st.cache_data(ttl=300, max_entries=100, show_spinner=False)
def _cached_ohlcv(ticker: str, **kwargs):
    return download_ohlcv(ticker, **kwargs)


@st.cache_data(ttl=60, max_entries=100, show_spinner=False)
def _cached_ohlcv_intraday(ticker: str, **kwargs):
    """Shorter TTL so 1D/5D minute charts stay lively."""
    return download_ohlcv(ticker, **kwargs)


@st.cache_data(ttl=300, max_entries=200, show_spinner=False)
def _cached_asset_info(ticker: str):
    return get_asset_info(ticker)


@st.cache_data(ttl=600, max_entries=200, show_spinner=False)
def _cached_quarterly_financials(ticker: str):
    return get_quarterly_financials(ticker)

PERIOD_MAP = {
    "1D": ("1d", "1m"),
    "5D": ("5d", "5m"),
    "1M": ("1mo", "1d"),
    "6M": ("6mo", "1d"),
    "YTD": ("ytd", "1d"),
    "1Y": ("1y", "1d"),
    "5Y": ("5y", "1wk"),
    "All": ("max", "1mo"),
}

# ═══════════════════════════════════════════════════════════
# Formatting helpers
# ═══════════════════════════════════════════════════════════
# Yahoo's fields are third-party data: a number can arrive as a string
# ("Infinity") and a name can hold any text. Figures go through _num, so an
# odd value shows as N/A instead of crashing the page, and text that reaches
# the page's HTML is escaped (audit B5-01, B5-03).

def _num(value):
    """A Yahoo field as a finite float, or None."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _text(value) -> str:
    """A Yahoo text field, safe to put in the page's HTML."""
    return html.escape(str(value))


def _currency_code(value):
    """A three-letter currency code (USD, EUR, GBp), or None."""
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z]{3}", value):
        return value
    return None


def _fmt_number(value, prefix="", suffix="", decimals=2):
    value = _num(value)
    if value is None:
        return "N/A"
    if abs(value) >= 1e12:
        return f"{prefix}{value/1e12:.{decimals}f}T{suffix}"
    if abs(value) >= 1e9:
        return f"{prefix}{value/1e9:.{decimals}f}B{suffix}"
    if abs(value) >= 1e6:
        return f"{prefix}{value/1e6:.{decimals}f}M{suffix}"
    return f"{prefix}{value:,.{decimals}f}{suffix}"


def _fmt_count(value):
    """Volumes: whole numbers below a million (they used to show .00, F1-14)."""
    number = _num(value)
    if number is not None and abs(number) < 1e6:
        return f"{number:,.0f}"
    return _fmt_number(value)


def _fmt_quote(value):
    """A price field: fmt_price (enough decimals under 1), or N/A."""
    value = _num(value)
    return "N/A" if value is None else fmt_price(value)


def _fmt_pct(value):
    value = _num(value)
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def _fmt_div_yield(value):
    if value is None:
        return "N/A"
    pct = value * 100
    if abs(pct) > 20:
        return "N/A"
    return f"{pct:.2f}%"


def _fmt_range(low, high):
    low, high = _num(low), _num(high)
    if low is not None and high is not None:
        return f"{fmt_price(low)} – {fmt_price(high)}"
    return "N/A"


def _fmt_supply(value):
    """Format supply numbers (crypto) in M/B."""
    value = _num(value)
    if value is None:
        return "N/A"
    if value >= 1e9:
        return f"{value/1e9:.2f}B"
    if value >= 1e6:
        return f"{value/1e6:.2f}M"
    return f"{value:,.0f}"


def _fmt_safe(value, fmt="{:.2f}", fallback="N/A"):
    """A figure in `fmt`, or the fallback when the field is missing or not a number."""
    value = _num(value)
    if value is None:
        return fallback
    return fmt.format(value)


def _fmt_date(value):
    """Format a Unix timestamp or date object to 'Mon D, YYYY' (no leading zero on day)."""
    if value is None:
        return "N/A"
    try:
        if isinstance(value, (int, float)):
            dt = _dt.datetime.fromtimestamp(int(value))
        elif isinstance(value, _dt.datetime):
            dt = value
        elif isinstance(value, _dt.date):
            dt = _dt.datetime(value.year, value.month, value.day)
        else:
            return "N/A"
        return dt.strftime("%b ") + str(dt.day) + dt.strftime(", %Y")
    except Exception:
        return "N/A"


# ═══════════════════════════════════════════════════════════
# Returns calculation
# ═══════════════════════════════════════════════════════════

def _calculate_returns(close_prices: pd.Series, current_price: float = None) -> dict:
    if close_prices.empty:
        return {}
        
    close_prices = close_prices.sort_index()
    close_prices.index = close_prices.index.tz_localize(None)
    # Yahoo pads some histories with closes of 0 (SHIB-USD: its first 217
    # days); a base of 0 printed "All +inf%" (found 2026-10-08)
    close_prices = close_prices[close_prices > 0]
    if close_prices.empty:
        return {}
    latest = current_price if current_price is not None else close_prices.iloc[-1]
    last_date = close_prices.index[-1]
    first_date = close_prices.index[0]
    
    returns = {}
    # Calendar-date offsets — matches Yahoo Finance methodology
    periods = {
        "5D": pd.DateOffset(weeks=1),
        "1M": pd.DateOffset(months=1),
        "6M": pd.DateOffset(months=6),
        "1Y": pd.DateOffset(years=1),
        "3Y": pd.DateOffset(years=3),
        "5Y": pd.DateOffset(years=5),
    }

    for label, offset in periods.items():
        try:
            target_date = last_date - offset
            if target_date >= first_date:
                idx = close_prices.index.asof(target_date)
                if pd.notna(idx):
                    base = close_prices.loc[idx]
                    returns[label] = (latest - base) / base
                else:
                    returns[label] = None
            else:
                returns[label] = None
        except Exception:
            returns[label] = None
            
    # YTD Calculation
    try:
        ytd_target = pd.Timestamp(year=last_date.year, month=1, day=1)
        if ytd_target >= first_date:
            idx = close_prices.index.asof(ytd_target)
            if pd.isna(idx): 
                idx = close_prices[close_prices.index.year == last_date.year].index[0]
            base = close_prices.loc[idx]
            returns["YTD"] = (latest - base) / base
        else:
            returns["YTD"] = None
    except Exception:
        returns["YTD"] = None

    # All-time / Max Calculation
    try:
        base = close_prices.iloc[0]
        returns["All"] = (latest - base) / base
    except Exception:
        returns["All"] = None

    return returns


# ═══════════════════════════════════════════════════════════
# Stat table builder (reusable for all tabs)
# ═══════════════════════════════════════════════════════════

def _build_stat_table(items):
    """Build a clean 2-column stat table from a list of (label, value) pairs.
    Filters out rows where value is 'N/A' to keep layout clean."""
    rows = ""
    for label, val in items:
        if val == "N/A":
            continue
        # Figures get same-width digits; text values (fund family) stay as is
        num = ' class="bl-num"' if str(val)[:1] in "$+-0123456789" else ""
        rows += (
            f'<div style="display:flex;justify-content:space-between;gap:1rem;padding:9px 0;'
            f'border-bottom:1px solid #F1F5F9;">'
            f'<span style="color:#64748B;font-size:0.9rem;">{label}</span>'
            f'<span{num} style="font-weight:600;color:#0A1628;font-size:0.9rem;text-align:right;">{_text(val)}</span>'
            f'</div>'
        )
    return f'<div style="padding:4px 0;">{rows}</div>'


def _render_metric_card(label, value, color="#0A1628"):
    """Render a single metric card for Financials section."""
    return (
        f'<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;'
        f'padding:16px;text-align:center;">'
        f'<div style="font-size:0.85rem;color:#64748B;margin-bottom:4px;">{label}</div>'
        f'<div class="bl-num" style="font-size:1.3rem;font-weight:700;color:{color};">{value}</div>'
        f'</div>'
    )


# ═══════════════════════════════════════════════════════════
# Tab renderers (one per section)
# ═══════════════════════════════════════════════════════════

def _render_key_stats(info, asset_type):
    """Render Key Statistics tab — adapts by asset type."""

    if asset_type in ("ETF", "INDEX"):
        left = [
            ("Previous Close", _fmt_quote(info.get('previous_close'))),
            ("Open", _fmt_quote(info.get('open_price'))),
            ("Day's Range", _fmt_range(info.get('day_low'), info.get('day_high'))),
        ]
        right = [
            ("52-Week Range", _fmt_range(info.get('fifty_two_week_low'), info.get('fifty_two_week_high'))),
            ("Volume", _fmt_count(info.get('volume'))),
            ("Avg. Volume", _fmt_count(info.get('avg_volume'))),
        ]

    elif asset_type == "CRYPTOCURRENCY":
        left = [
            ("Previous Close", _fmt_quote(info.get('previous_close'))),
            ("Open", _fmt_quote(info.get('open_price'))),
            ("Day's Range", _fmt_range(info.get('day_low'), info.get('day_high'))),
            ("52-Week Range", _fmt_range(info.get('fifty_two_week_low'), info.get('fifty_two_week_high'))),
        ]
        right = [
            ("Market Cap", _fmt_number(info.get('market_cap'))),
            ("Circulating Supply", _fmt_supply(info.get('circulating_supply'))),
            ("Max Supply", _fmt_supply(info.get('max_supply'))),
            ("Volume (24h)", _fmt_count(info.get('volume_24h'))),
        ]

    else:  # EQUITY (default)
        bid = _num(info.get('bid'))
        bid_size = _num(info.get('bid_size'))
        ask = _num(info.get('ask'))
        ask_size = _num(info.get('ask_size'))

        if bid and bid_size:
            bid_str = f"{fmt_price(bid)} x {int(bid_size):,}"
        elif bid:
            bid_str = fmt_price(bid)
        else:
            bid_str = "N/A"

        if ask and ask_size:
            ask_str = f"{fmt_price(ask)} x {int(ask_size):,}"
        elif ask:
            ask_str = fmt_price(ask)
        else:
            ask_str = "N/A"

        div_rate = _num(info.get('dividend_rate'))
        div_yield = _num(info.get('dividend_yield'))
        if div_rate is not None and div_yield is not None:
            fwd_div_str = f"{div_rate:.2f} ({div_yield * 100:.2f}%)"
        elif div_rate is not None:
            fwd_div_str = f"{div_rate:.2f}"
        elif div_yield is not None:
            fwd_div_str = f"{div_yield * 100:.2f}%"
        else:
            fwd_div_str = "N/A"

        left = [
            ("Previous Close", _fmt_quote(info.get('previous_close'))),
            ("Open", _fmt_quote(info.get('open_price'))),
            ("Bid", bid_str),
            ("Ask", ask_str),
            ("Day's Range", _fmt_range(info.get('day_low'), info.get('day_high'))),
            ("52 Week Range", _fmt_range(info.get('fifty_two_week_low'), info.get('fifty_two_week_high'))),
            ("Volume", _fmt_count(info.get('volume'))),
            ("Avg. Volume", _fmt_count(info.get('avg_volume'))),
        ]
        right = [
            ("Market Cap (intraday)", _fmt_number(info.get('market_cap'))),
            ("Beta (5Y Monthly)", _fmt_safe(info.get('beta'))),
            ("PE Ratio (TTM)", _fmt_safe(info.get('pe_ratio'))),
            ("EPS (TTM)", _fmt_safe(info.get('eps'), "{:,.2f}")),
            ("Earnings Date (est.)", _fmt_date(info.get('next_earnings_date'))),
            ("Dividend & Trailing Yield" if info.get('dividend_yield_trailing')
             else "Forward Dividend & Yield", fwd_div_str),
            ("Ex-Dividend Date", _fmt_date(info.get('ex_dividend_date'))),
            ("1y Target Est", _fmt_quote(info.get('target_mean_price'))),
        ]

    # Check if any data is actually available (not all N/A)
    all_items = left + right
    has_data = any(v != "N/A" for _, v in all_items)

    if not has_data:
        st.info("Market data is temporarily unavailable, probably because Yahoo Finance is limiting requests. Try again in a few seconds.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(_build_stat_table(left), unsafe_allow_html=True)
    with col2:
        st.markdown(_build_stat_table(right), unsafe_allow_html=True)


def _quarter_label(dt) -> str:
    """
    Label a quarter by the month it ends ('Sep 2025').

    Fiscal years differ by company (Apple's quarter ending in September is
    its fiscal Q4), so a calendar label like 'Q3 FY25' would be wrong for many.
    """
    return dt.strftime("%b %Y")


def _render_performance(ticker: str, hist_close: pd.Series, price, spy_close: pd.Series):
    """Render Performance Overview tab — trailing returns for ticker vs S&P 500."""

    def _fmt_ret(r):
        if r is None:
            return "N/A", "#94A3B8"
        color = "#16A34A" if r >= 0 else "#DC2626"
        sign = "+" if r >= 0 else ""
        return f"{sign}{r * 100:.2f}%", color

    spy_price = spy_close.iloc[-1] if not spy_close.empty else None
    ticker_rets = _calculate_returns(hist_close, current_price=price) if price else {}
    spy_rets = _calculate_returns(spy_close, current_price=spy_price) if spy_price else {}

    # Reference date note
    note_date = ""
    if not hist_close.empty:
        try:
            note_date = hist_close.index[-1].strftime("%m/%d/%Y")
        except Exception:
            pass

    st.markdown(
        f'<div style="font-size:0.82rem;color:#64748B;margin-bottom:1.2rem;">'
        f'Trailing price returns as of {note_date}, from closing prices adjusted for splits only, '
        f'so dividends are not included. Benchmark: the S&amp;P 500 price index (^GSPC).</div>',
        unsafe_allow_html=True,
    )

    periods_cfg = [
        ("YTD Return", "YTD"),
        ("1-Year Return", "1Y"),
        ("3-Year Return", "3Y"),
        ("5-Year Return", "5Y"),
    ]

    row1 = st.columns(2)
    row2 = st.columns(2)
    grid = [row1[0], row1[1], row2[0], row2[1]]

    for col, (period_label, period_key) in zip(grid, periods_cfg):
        t_ret = ticker_rets.get(period_key)
        s_ret = spy_rets.get(period_key)
        t_str, t_color = _fmt_ret(t_ret)
        s_str, s_color = _fmt_ret(s_ret)

        with col:
            st.markdown(
                f'<div style="border:1px solid #E2E8F0;border-radius:12px;padding:20px;'
                f'background:white;margin-bottom:1rem;">'
                f'<div style="font-size:0.9rem;font-weight:600;color:#0A1628;margin-bottom:14px;">'
                f'{period_label}</div>'
                f'<div style="margin-bottom:12px;">'
                f'<div style="font-size:0.8rem;color:#64748B;margin-bottom:2px;">{ticker}</div>'
                f'<div class="bl-num" style="font-size:1.9rem;font-weight:700;color:{t_color};">{t_str}</div>'
                f'</div>'
                f'<div style="border-top:1px solid #F1F5F9;padding-top:10px;">'
                f'<div style="font-size:0.8rem;color:#64748B;margin-bottom:2px;">S&amp;P 500 (^GSPC)</div>'
                f'<div class="bl-num" style="font-size:1.3rem;font-weight:600;color:{s_color};">{s_str}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

def _render_revenue(fin_df: pd.DataFrame, currency: str = None):
    """Render Revenue vs. Earnings tab — grouped bar chart by quarter.

    `currency` is the financial statements' currency, which can differ from
    the quote's (Taiwan Semiconductor's US listing reports in TWD).
    """

    if fin_df.empty:
        # Yahoo answered and has no statements (a failed request is told apart
        # by the caller)
        st.info("Yahoo Finance has no quarterly results for this asset.")
        return

    df = fin_df.tail(4)
    q_labels = [_quarter_label(dt) for dt in df.index]
    revenues = df['revenue'].tolist() if 'revenue' in df.columns else []
    net_incomes = df['net_income'].tolist() if 'net_income' in df.columns else []

    all_fin_vals = [v for v in revenues + net_incomes if v is not None and pd.notna(v)]
    if not all_fin_vals:
        st.info("Financial data not available.")
        return

    max_v = max(abs(v) for v in all_fin_vals)
    if max_v >= 1e9:
        scale, suffix = 1e9, "B"
    elif max_v >= 1e6:
        scale, suffix = 1e6, "M"
    else:
        scale, suffix = 1e3, "K"

    def _sc(vals):
        return [v / scale if v is not None and pd.notna(v) else None for v in vals]

    unit = f" {currency}" if currency else ""
    st.caption(
        "Quarterly revenue and net income by the month each quarter ends"
        + (f", in {currency}." if currency else ".")
    )

    fig = go.Figure()
    if revenues:
        fig.add_trace(go.Bar(
            x=q_labels, y=_sc(revenues), name='Revenue',
            marker_color='#2E6FC7',
            hovertemplate=f'Revenue: %{{y:.2f}}{suffix}{unit}<extra></extra>',
        ))
    if net_incomes:
        fig.add_trace(go.Bar(
            x=q_labels, y=_sc(net_incomes), name='Earnings',
            marker_color='#F59E0B',
            hovertemplate=f'Earnings: %{{y:.2f}}{suffix}{unit}<extra></extra>',
        ))

    fig.update_layout(
        barmode='group', height=300,
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=20, b=40),
        showlegend=True,
        legend=dict(orientation='h', y=1.12, x=0, xanchor='left', font=dict(size=11)),
        yaxis=dict(ticksuffix=suffix, tickformat='.2f'),
    )
    apply_brand_layout(fig)
    st.plotly_chart(fig, width='stretch', config={'scrollZoom': False})

def _render_fund_details(info):
    """Render Fund Details tab (ETFs only)."""
    items = [
        ("Fund Family", info.get('fund_family') or "N/A"),
        ("Net Assets", _fmt_number(info.get('net_assets'))),
        ("NAV", _fmt_quote(info.get('nav_price'))),
        ("Expense Ratio", _fmt_pct(info.get('expense_ratio'))),
        ("Yield", _fmt_pct(info.get('yield_pct'))),
        ("YTD Return", _fmt_pct(info.get('ytd_return'))),
        ("Beta (5Y)", _fmt_safe(info.get('beta'))),
        ("P/E Ratio (TTM)", _fmt_safe(info.get('pe_ratio'))),
    ]
    col1, col2 = st.columns(2)
    left = items[:4]
    right = items[4:]
    with col1:
        st.markdown(_build_stat_table(left), unsafe_allow_html=True)
    with col2:
        st.markdown(_build_stat_table(right), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# Main page
# ═══════════════════════════════════════════════════════════

def main():
    """Stocks main page."""

    # ── Page Header ──
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h1 class="page-title">Stocks</h1>
        <p class="page-subtitle">Look up any stock, ETF, crypto asset or index with market data from Yahoo Finance.</p>
    </div>
    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # Search bar — empty by default, user must click Search
    # ═══════════════════════════════════════════════════════
    # Inject search bar styling — perfectly align search button with input
    st.markdown("""
    <style>
    /* Align bottom edges to account for label gap */
    [data-testid="stHorizontalBlock"] > div:has(button) {
        display: flex;
        align-items: flex-end;
    }
    /* Match the search button to the input's height */
    [data-testid="stHorizontalBlock"] > div:has(button) button {
        height: 44px !important;
        min-height: 44px !important;
        padding: 0 1rem !important;
        margin-bottom: 0px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_pad_l, col_input, col_search, col_pad_r = st.columns([0.5, 3, 0.7, 0.5])

    with col_input:
        ticker_input = st.text_input(
            "Ticker symbol",
            value="",
            placeholder="e.g. AAPL, VOO, BTC-USD or ^GSPC",
            help="Stocks, ETFs, crypto (BTC-USD), indices (^GSPC): any Yahoo Finance symbol",
            label_visibility="collapsed",
        ).strip().upper()

    with col_search:
        search_clicked = st.button("Search", icon=":material/search:", type="primary", width="stretch")

    # Validate: reject multiple symbols (comma/space separated)
    _is_multi = len([t for t in ticker_input.replace(',', ' ').split() if t]) > 1
    # Yahoo Finance symbol allowlist (BRK-B, BF.B, ^GSPC, BTC-USD, EURUSD=X).
    # Rejecting anything else avoids a pointless network round-trip and keeps
    # arbitrary text out of the page.
    _is_valid_symbol = bool(re.fullmatch(TICKER_PATTERN, ticker_input))

    # Track searched ticker in session state
    if search_clicked and ticker_input:
        if _is_multi:
            st.warning("Enter **one symbol at a time** (e.g. `AAPL`): this page looks up a single asset.")
            st.session_state['stocks_ticker'] = None
        elif not _is_valid_symbol:
            st.warning(f"**{escape_markdown(ticker_input)}** is not a valid ticker symbol. Use letters, digits and `.` `-` `^` `=` only (e.g. `AAPL`, `BRK-B`, `^GSPC`, `BTC-USD`).")
            st.session_state['stocks_ticker'] = None
        else:
            st.session_state['stocks_ticker'] = ticker_input
    elif 'stocks_ticker' not in st.session_state:
        st.session_state['stocks_ticker'] = None

    active_ticker = st.session_state.get('stocks_ticker')

    if not active_ticker:
        # Empty state: what to do, with examples (a drawn icon, not an emoji)
        st.markdown("""
        <div style="text-align:center;padding:72px 20px;">
            <svg aria-hidden="true" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:10px;"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
            <div style="font-size:1.05rem;font-weight:600;color:#0A1628;">Search for any stock</div>
            <div style="font-size:0.95rem;color:#64748B;margin-top:4px;">Or an ETF, a crypto asset or an index: try AAPL, VOO, BTC-USD or ^GSPC.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ═══════════════════════════════════════════════════════
    # Fetch data
    # ═══════════════════════════════════════════════════════
    yf_period, yf_interval = PERIOD_MAP["1Y"]

    # Prices and details are fetched apart: the page works with prices
    # alone, and each failure gets its own message (audit B3-08, B3-09)
    no_prices_msg = (
        f"**No prices for {active_ticker}**: Yahoo Finance returned none. Check the symbol; "
        "if it is right, Yahoo may be limiting requests, so try again in a minute."
    )
    with st.spinner(f"Loading {active_ticker}..."):
        try:
            # auto_adjust=False: the quoted closes (adjusted for splits only),
            # as Yahoo charts them and as the returns strip computes them.
            # The default would also subtract past dividends.
            ohlcv = _cached_ohlcv(active_ticker, period=yf_period, interval=yf_interval,
                                  auto_adjust=False)
        except Exception:
            logger.warning("Price download failed for %s", active_ticker, exc_info=True)
            st.error(no_prices_msg)
            return
        try:
            info = _cached_asset_info(active_ticker)
            info_failed = False
        except Exception:
            # Not cached (st.cache_data keeps only results): the next visit retries
            logger.warning("Asset details failed for %s", active_ticker, exc_info=True)
            info, info_failed = {}, True

    if ohlcv.empty:
        st.error(no_prices_msg)
        return
    if info_failed:
        st.info("Yahoo Finance did not send this asset's details just now, so its name, statistics "
                "and type may be missing. Try again in a minute.")

    # ═══════════════════════════════════════════════════════
    # Determine asset type
    # ═══════════════════════════════════════════════════════
    asset_type = (info.get('type') or 'EQUITY').upper()

    # ═══════════════════════════════════════════════════════
    # Price Header
    # ═══════════════════════════════════════════════════════
    price = _num(info.get('price'))
    prev_close = _num(info.get('previous_close'))
    # Yahoo's text goes into the page's HTML below: escaped (audit B5-01)
    name = _text(info.get('name') or active_ticker)
    sector = _text(info['sector']) if info.get('sector') else None
    industry = _text(info['industry']) if info.get('industry') else None

    if price and prev_close:
        change = price - prev_close
        change_pct = (change / prev_close) * 100
    else:
        change, change_pct = None, None

    # Sector/industry or asset-type tag, one quiet style for all
    tag_text = None
    if sector:
        tag_text = sector + (f' · {industry}' if industry else '')
    elif asset_type == "ETF":
        fund_family = info.get('fund_family')
        tag_text = 'ETF' + (f' · {_text(fund_family)}' if fund_family else '')
    elif asset_type == "CRYPTOCURRENCY":
        tag_text = 'Crypto'
    elif asset_type == "INDEX":
        tag_text = 'Index'
    tag_html = (
        f'<span style="background:#F1F5F9;color:#334155;padding:3px 10px;border-radius:12px;'
        f'font-size:0.8rem;font-weight:500;margin-left:12px;white-space:nowrap;">{tag_text}</span>'
        if tag_text else ""
    )

    # Index levels are points; everything else is quoted in a currency
    currency = _currency_code(info.get('currency')) if asset_type != "INDEX" else None
    currency_html = (
        f'<span style="color:#64748B;font-size:1rem;margin-left:8px;">{currency}</span>'
        if currency else ""
    )

    if price:
        chg_str = ""
        if change is not None and change_pct is not None:
            chg_color = "#16A34A" if change >= 0 else "#DC2626"
            chg_sign = "+" if change >= 0 else ""
            chg_str = (
                f'<span class="bl-num" style="color:{chg_color};font-size:1.1rem;font-weight:600;margin-left:12px;">'
                f'{chg_sign}{fmt_price(change)} ({chg_sign}{change_pct:.2f}%)</span>'
            )
        st.markdown(
            f'<div style="margin-bottom:0.3rem;">'
            f'<span style="font-size:1.3rem;font-weight:700;color:#0A1628;">{name}</span>'
            f'<span style="color:#64748B;margin-left:8px;">({active_ticker})</span>'
            f'{tag_html}'
            f'</div>'
            f'<div style="margin-bottom:0.8rem;">'
            f'<span class="bl-num" style="font-size:2.2rem;font-weight:700;color:#0A1628;">{fmt_price(price)}</span>'
            f'{currency_html}'
            f'{chg_str}'
            f'</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # Chart
    # ═══════════════════════════════════════════════════════
    ctrl1, ctrl2 = st.columns([4, 1.5])
    with ctrl1:
        period_label = st.radio(
            "Period", options=list(PERIOD_MAP.keys()),
            index=5, horizontal=True, label_visibility="collapsed"
        )
    with ctrl2:
        chart_type = st.radio(
            "Chart", options=["Line", "Candles"],
            horizontal=True, label_visibility="collapsed"
        )

    yf_period, yf_interval = PERIOD_MAP[period_label]
    is_intraday = yf_interval not in ("1d", "1wk", "1mo")
    # The 1Y daily data loaded above serves the 1Y chart; any other period
    # downloads its own. If that fails, say so: the 1Y data used to be drawn
    # under the new period's label, in silence (audit B3-01).
    chart_ohlcv = ohlcv
    if (yf_period, yf_interval) != PERIOD_MAP.get("1Y"):
        try:
            # Extended hours for 1D and 5D equity charts (not crypto).
            # Diagnostic confirmed 5D prepost data is clean: sorted, no zeros, no NaN, no >5% jumps.
            use_prepost = (period_label in ("1D", "5D")) and (asset_type != "CRYPTOCURRENCY")
            # 5D: the last five sessions, like the 5D figure of the returns
            # strip (one calendar week). Nine days back always holds five, even
            # across a long weekend; they are trimmed below. Starting five
            # calendar days back showed four sessions most days (audit F1-04).
            _dl = _cached_ohlcv_intraday if is_intraday else _cached_ohlcv
            if period_label == "5D":
                _start_5d = (_dt.datetime.now() - _dt.timedelta(days=9)).strftime("%Y-%m-%d")
                chart_ohlcv = _dl(active_ticker, start=_start_5d,
                            interval=yf_interval, prepost=use_prepost, auto_adjust=False)
            else:
                chart_ohlcv = _dl(active_ticker, period=yf_period,
                            interval=yf_interval, prepost=use_prepost, auto_adjust=False)
            if is_intraday and chart_ohlcv.index.tz is not None:
                try:
                    chart_ohlcv.index = chart_ohlcv.index.tz_convert('America/New_York').tz_localize(None)
                except Exception:
                    chart_ohlcv.index = chart_ohlcv.index.tz_localize(None)
            if period_label == "5D" and not chart_ohlcv.empty:
                sessions = chart_ohlcv.index.normalize().unique()
                chart_ohlcv = chart_ohlcv[chart_ohlcv.index.normalize() >= sessions[-5:].min()]

            # --- INTRADAY PADDING: fill empty bars up to market end ---
            if period_label == "1D" and not chart_ohlcv.empty:
                last_ts = chart_ohlcv.index[-1]
                last_date = last_ts.date()
                
                if asset_type == "CRYPTOCURRENCY":
                    end_hour, end_min = 23, 59
                elif use_prepost:
                    end_hour, end_min = 20, 0  # 8 PM — US after-market end
                else:
                    end_hour, end_min = 16, 0  # 4 PM — regular close
                    
                end_dt = pd.Timestamp(_dt.datetime.combine(last_date, _dt.time(end_hour, end_min)))
                
                if last_ts < end_dt:
                    freq_str = yf_interval.replace('m', 'min').replace('h', 'H')
                    freq = pd.Timedelta(freq_str)
                    future_index = pd.date_range(start=last_ts + freq, end=end_dt, freq=freq)
                    if not future_index.empty:
                        empty_df = pd.DataFrame(index=future_index, columns=chart_ohlcv.columns)
                        chart_ohlcv = pd.concat([chart_ohlcv, empty_df])
        except Exception:
            logger.warning("%s chart download failed for %s", period_label, active_ticker, exc_info=True)
            chart_ohlcv = None

    if chart_ohlcv is None or chart_ohlcv.empty:
        st.warning(f"The {period_label} chart could not be loaded from Yahoo Finance right now. "
                   "Try again in a moment, or pick another period.")
    else:
        st.plotly_chart(
            create_price_chart(chart_ohlcv, active_ticker, chart_type,
                               prev_close=prev_close, is_intraday=is_intraday),
            width='stretch', config={'scrollZoom': False}
        )

    # ═══════════════════════════════════════════════════════
    # Period Returns Strip
    # Uses auto_adjust=False (split-adj, no dividend adj) + max history
    # to match Yahoo Finance return calculations exactly.
    # ═══════════════════════════════════════════════════════
    hist_close = pd.Series(dtype=float)
    try:
        hist_raw = _cached_ohlcv(active_ticker, period="max", interval="1d", auto_adjust=False)
        hist_close = hist_raw["Close"].squeeze().dropna()
        rets = _calculate_returns(hist_close, current_price=price)
    except Exception:
        # The strip then shows dashes; the cause goes to the log (audit B3-14)
        logger.warning("Full history failed for %s", active_ticker, exc_info=True)
        rets = {}
        
    day_ret = ((price - prev_close) / prev_close) if price and prev_close and prev_close != 0 else None

    ret_items = [
        ("1D", day_ret), ("5D", rets.get("5D")), ("1M", rets.get("1M")),
        ("6M", rets.get("6M")), ("YTD", rets.get("YTD")),
        ("1Y", rets.get("1Y")), ("5Y", rets.get("5Y")), ("All", rets.get("All")),
    ]

    cells = ""
    for label, val in ret_items:
        if val is not None:
            color = "#16A34A" if val >= 0 else "#DC2626"
            # Whole percents from 1,000% up (AAPL's All: +265,132%), so the
            # figure fits a phone's four-column grid without breaking
            pct_str = f"{val:+,.0%}" if abs(val) >= 10 else f"{val:+.2%}"
        else:
            color, pct_str = "#94A3B8", "—"
        cells += (
            '<div>'
            f'<div class="bl-returns-label">{label}</div>'
            f'<div class="bl-num bl-returns-value" style="color:{color};">{pct_str}</div>'
            '</div>'
        )
    # A grid (utils/styles.py, .bl-returns): one row of eight, two rows of
    # four on phones. It used to scroll sideways with a hidden scrollbar, so
    # 5Y and All sat off screen, the figures collided and the keyboard could
    # not reach them (audit F3-03, F4-01).
    st.markdown(f'<div class="bl-returns">{cells}</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # Additional data for EQUITY tabs (cached — fast on re-render)
    # ═══════════════════════════════════════════════════════
    spy_close = pd.Series(dtype=float)
    quarterly_fin_df = pd.DataFrame()
    financials_failed = False

    if asset_type == "EQUITY":
        try:
            _spy_raw = _cached_ohlcv('^GSPC', period='max', interval='1d', auto_adjust=False)
            spy_close = _spy_raw['Close'].squeeze().dropna()
        except Exception:
            logger.warning("S&P 500 history failed", exc_info=True)
        try:
            quarterly_fin_df = _cached_quarterly_financials(active_ticker)
        except Exception:
            # A failed request, not an asset without statements (audit B3-08)
            logger.warning("Quarterly financials failed for %s", active_ticker, exc_info=True)
            financials_failed = True

    # ═══════════════════════════════════════════════════════
    # Adaptive Tabs
    # ═══════════════════════════════════════════════════════

    if asset_type == "EQUITY":
        tab_stats, tab_perf, tab_rev = st.tabs([
            "Key statistics", "Performance", "Revenue and earnings",
        ])
        with tab_stats:
            _render_key_stats(info, asset_type)
        with tab_perf:
            if spy_close.empty:
                st.caption("The S&P 500 comparison could not be loaded just now.")
            _render_performance(active_ticker, hist_close, price, spy_close)
        with tab_rev:
            if financials_failed:
                st.info("Yahoo Finance did not send the quarterly results just now. Try again in a minute.")
            else:
                _render_revenue(quarterly_fin_df,
                                _currency_code(info.get('financial_currency'))
                                or _currency_code(info.get('currency')))

    elif asset_type == "ETF":
        tab_stats, tab_fund = st.tabs(["Market data", "Fund details"])
        with tab_stats:
            _render_key_stats(info, asset_type)
        with tab_fund:
            _render_fund_details(info)

    elif asset_type == "CRYPTOCURRENCY":
        tab_stats, = st.tabs(["Market and supply"])
        with tab_stats:
            _render_key_stats(info, asset_type)

    elif asset_type == "INDEX":
        tab_stats, = st.tabs(["Market data"])
        with tab_stats:
            _render_key_stats(info, asset_type)

    else:
        # Unknown type — show basic overview
        tab_stats, = st.tabs(["Overview"])
        with tab_stats:
            _render_key_stats(info, "EQUITY")


    # ── Render Footer ──
    from utils.styles import render_footer
    render_footer()

if __name__ == "__main__":
    main()
