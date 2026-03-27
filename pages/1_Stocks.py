"""
Stocks – Yahoo Finance-inspired adaptive asset explorer.
"""

import sys
import os
import logging
import datetime as _dt

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# ── Paths ────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

st.set_page_config(
    page_title="Stocks – PortfolioLab",
    page_icon="📊",
    layout="wide",
)

from utils.styles import inject_critical_css, inject_styles, render_navbar  # noqa: E402
inject_critical_css()
inject_styles()
render_navbar(active_page="stocks")

from core.data_provider import (  # noqa: E402
    download_ohlcv, get_asset_info, get_quarterly_financials,
)

logger = logging.getLogger(__name__)

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

def _fmt_number(value, prefix="", suffix="", decimals=2):
    if value is None:
        return "N/A"
    if abs(value) >= 1e12:
        return f"{prefix}{value/1e12:.{decimals}f}T{suffix}"
    if abs(value) >= 1e9:
        return f"{prefix}{value/1e9:.{decimals}f}B{suffix}"
    if abs(value) >= 1e6:
        return f"{prefix}{value/1e6:.{decimals}f}M{suffix}"
    return f"{prefix}{value:,.{decimals}f}{suffix}"


def _fmt_pct(value):
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
    if low is not None and high is not None:
        return f"{low:,.2f} – {high:,.2f}"
    return "N/A"


def _fmt_supply(value):
    """Format supply numbers (crypto) in M/B."""
    if value is None:
        return "N/A"
    if value >= 1e9:
        return f"{value/1e9:.2f}B"
    if value >= 1e6:
        return f"{value/1e6:.2f}M"
    return f"{value:,.0f}"


def _fmt_safe(value, fmt="{:.2f}", fallback="N/A"):
    """Generic safe formatter."""
    if value is None:
        return fallback
    try:
        return fmt.format(value)
    except (ValueError, TypeError):
        return str(value)


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
# Chart builder
# ═══════════════════════════════════════════════════════════

def _create_price_chart(ohlcv, ticker, chart_type, prev_close=None, is_intraday=False):
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03, row_heights=[0.8, 0.2],
    )

    x_vals = list(range(len(ohlcv))) if is_intraday else ohlcv.index

    # Prepare custom hover data
    custom_data = []
    for i in range(len(ohlcv)):
        ts_val = ohlcv.index[i]
        if hasattr(ts_val, "strftime"):
            date_str = ts_val.strftime("%m/%d %I:%M %p").replace(" 0", " ") if is_intraday else ts_val.strftime("%m/%d/%Y")
        else:
            date_str = str(ts_val)
        c = ohlcv['Close'].iloc[i] if not pd.isna(ohlcv['Close'].iloc[i]) else 0
        o = ohlcv['Open'].iloc[i] if not pd.isna(ohlcv['Open'].iloc[i]) else 0
        h = ohlcv['High'].iloc[i] if not pd.isna(ohlcv['High'].iloc[i]) else 0
        l = ohlcv['Low'].iloc[i] if not pd.isna(ohlcv['Low'].iloc[i]) else 0
        v = ohlcv['Volume'].iloc[i] if 'Volume' in ohlcv.columns and not pd.isna(ohlcv['Volume'].iloc[i]) else 0
        custom_data.append([date_str, f"{c:,.2f}", f"{o:,.2f}", f"{h:,.2f}", f"{l:,.2f}", f"{v:,.0f}"])

    hover_temp = (
        "<b>Date:         %{customdata[0]}</b><br><br>"
        "Close:       %{customdata[1]}<br>"
        "Open:        %{customdata[2]}<br>"
        "High:         %{customdata[3]}<br>"
        "Low:          %{customdata[4]}<br>"
        "Volume:    %{customdata[5]}"
        "<extra></extra>"
    )

    if chart_type == "Candles":
        fig.add_trace(go.Candlestick(
            x=x_vals, open=ohlcv['Open'], high=ohlcv['High'],
            low=ohlcv['Low'], close=ohlcv['Close'], name=ticker,
            increasing_line_color='#10B981', decreasing_line_color='#EF4444',
            showlegend=False, customdata=custom_data, hovertemplate=hover_temp,
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=x_vals, y=ohlcv['Close'], mode='lines', name=ticker,
            line=dict(color='#2E6FC7', width=2),
            fill='tozeroy' if not is_intraday else None,
            fillcolor='rgba(46,111,199,0.08)' if not is_intraday else None,
            showlegend=False, customdata=custom_data, hovertemplate=hover_temp,
        ), row=1, col=1)

    colors = ['#10B981' if c >= o else '#EF4444'
              for c, o in zip(ohlcv['Close'], ohlcv['Open'])]
    fig.add_trace(go.Bar(
        x=x_vals, y=ohlcv['Volume'], marker_color=colors,
        opacity=0.4, name='Volume', showlegend=False,
        hoverinfo='skip'
    ), row=2, col=1)

    fig.update_layout(
        height=480, margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis_rangeslider_visible=False,
        showlegend=False,
        font=dict(family="Inter, sans-serif")
    )

    if prev_close and is_intraday:
        fig.add_hline(
            y=prev_close, line_dash="dash", line_color="#94A3B8", line_width=1, row=1, col=1,
            annotation_text=f"Prev Close {prev_close:,.2f}",
            annotation_position="right", annotation_font_color="#94A3B8", annotation_font_size=10,
        )

    for ax in ['xaxis', 'xaxis2', 'yaxis', 'yaxis2']:
        fig.update_layout(**{ax: dict(gridcolor='#D1D5DB', zerolinecolor='#D1D5DB', showgrid=True)})

    if is_intraday:
        timestamps = ohlcv.index
        if hasattr(timestamps, 'tz') and timestamps.tz is not None:
            timestamps = timestamps.tz_localize(None)
        tickvals, ticktext, prev_date = [], [], None
        num_days = len(set(ts.date() for ts in timestamps))
        for i, ts in enumerate(timestamps):
            current_date = ts.date()
            if current_date != prev_date:
                if prev_date is not None:
                    fig.add_vline(x=i - 0.5, line_dash="dot", line_color="#CBD5E1", line_width=1, row='all', col=1)
                if num_days > 1:
                    tickvals.append(i)
                    ticktext.append(ts.strftime("%b %d"))
                prev_date = current_date
            if ts.minute == 0:
                if num_days == 1:
                    tickvals.append(i)
                    ticktext.append(ts.strftime("%I %p").lstrip("0").replace(" ", "\n"))
                elif ts.hour in (12, 15) and ts.hour != 9:
                    tickvals.append(i)
                    ticktext.append(ts.strftime("%I %p").lstrip("0"))
        fig.update_xaxes(tickvals=tickvals, ticktext=ticktext, type="linear", row=1, col=1)
        fig.update_xaxes(tickvals=tickvals, ticktext=ticktext, type="linear", row=2, col=1)

        # ── Pre/Post-market markers and shading ──────────────────────────────
        # Collect per-day boundary indices
        from collections import defaultdict as _dd
        day_idx = _dd(list)
        for i, ts in enumerate(timestamps):
            day_idx[ts.date()].append(i)

        mkt_open_indices  = []  # index of first bar at/after 9:30 AM per day
        mkt_close_indices = []  # index of first bar at/after 4:00 PM  per day

        for date_key in sorted(day_idx):
            idxs = day_idx[date_key]
            open_i = close_i = None
            for i in idxs:
                ts = timestamps[i]
                if open_i is None and (ts.hour > 9 or (ts.hour == 9 and ts.minute >= 30)):
                    open_i = i
                if close_i is None and ts.hour >= 16:
                    close_i = i
            if open_i is not None:  mkt_open_indices.append((idxs[0],  open_i))
            if close_i is not None: mkt_close_indices.append((close_i, idxs[-1]))

        has_extended = bool(mkt_open_indices or mkt_close_indices)

        if has_extended:
            # Shade pre-market and post-market zones (light gray, behind data)
            for start_i, open_i in mkt_open_indices:
                if open_i > start_i:
                    fig.add_vrect(x0=start_i - 0.5, x1=open_i - 0.5,
                                  fillcolor="#EFF2F7", opacity=0.55,
                                  layer="below", line_width=0)
            for close_i, end_i in mkt_close_indices:
                if end_i > close_i:
                    fig.add_vrect(x0=close_i - 0.5, x1=end_i + 0.5,
                                  fillcolor="#EFF2F7", opacity=0.55,
                                  layer="below", line_width=0)

            # For 1D only: show labeled Mkt Open / Mkt Close vlines
            if num_days == 1:
                if mkt_open_indices:
                    _, open_i = mkt_open_indices[0]
                    fig.add_vline(x=open_i, line_dash="dot", line_color="#94A3B8",
                                  line_width=1, row='all', col=1,
                                  annotation_text="Mkt Open", annotation_position="top",
                                  annotation_font_size=9, annotation_font_color="#94A3B8")
                if mkt_close_indices:
                    close_i, _ = mkt_close_indices[0]
                    fig.add_vline(x=close_i, line_dash="dot", line_color="#94A3B8",
                                  line_width=1, row='all', col=1,
                                  annotation_text="Mkt Close", annotation_position="top",
                                  annotation_font_size=9, annotation_font_color="#94A3B8")

    # Calculate dynamic Y-axis range to avoid flattening on short periods
    if chart_type == "Candles":
        y_min = ohlcv['Low'].min()
        y_max = ohlcv['High'].max()
    else:
        y_min = ohlcv['Close'].min()
        y_max = ohlcv['Close'].max()
        
    if prev_close and is_intraday:
        y_min = min(y_min, prev_close)
        y_max = max(y_max, prev_close)
        
    y_padding = (y_max - y_min) * 0.1
    if y_padding == 0:
        y_padding = y_max * 0.05 if y_max != 0 else 1.0
        
    fig.update_yaxes(title_text="Price", range=[y_min - y_padding, y_max + y_padding], side="right", row=1, col=1)
    fig.update_yaxes(title_text="Vol", side="right", row=2, col=1)
    return fig


# ═══════════════════════════════════════════════════════════
# Stat table builder (reusable for all tabs)
# ═══════════════════════════════════════════════════════════

def _build_stat_table(items):
    """Build a clean 2-column stat table from a list of (label, value) pairs.
    Filters out rows where value is 'N/A' to keep layout clean."""
    html = ""
    for label, val in items:
        if val == "N/A":
            continue
        html += (
            f'<div style="display:flex;justify-content:space-between;padding:8px 0;'
            f'border-bottom:1px solid #F1F5F9;">'
            f'<span style="color:#64748B;font-size:0.85rem;">{label}</span>'
            f'<span style="font-weight:600;color:#1E3A5F;font-size:0.85rem;">{val}</span>'
            f'</div>'
        )
    return f'<div style="padding:4px 0;">{html}</div>'


def _render_metric_card(label, value, color="#1E3A5F"):
    """Render a single metric card for Financials section."""
    return (
        f'<div style="background:white;border:1px solid #E2E8F0;border-radius:12px;'
        f'padding:16px;text-align:center;">'
        f'<div style="font-size:0.75rem;color:#64748B;text-transform:uppercase;'
        f'letter-spacing:0.05em;margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:1.3rem;font-weight:700;color:{color};">{value}</div>'
        f'</div>'
    )


# ═══════════════════════════════════════════════════════════
# Tab renderers (one per section)
# ═══════════════════════════════════════════════════════════

def _render_key_stats(info, asset_type):
    """Render Key Statistics tab — adapts by asset type."""

    if asset_type in ("ETF", "INDEX"):
        left = [
            ("Previous Close", _fmt_safe(info.get('previous_close'), "${:,.2f}")),
            ("Open", _fmt_safe(info.get('open_price'), "${:,.2f}")),
            ("Day's Range", _fmt_range(info.get('day_low'), info.get('day_high'))),
        ]
        right = [
            ("52-Week Range", _fmt_range(info.get('fifty_two_week_low'), info.get('fifty_two_week_high'))),
            ("Volume", _fmt_number(info.get('volume'))),
            ("Avg. Volume", _fmt_number(info.get('avg_volume'))),
        ]

    elif asset_type == "CRYPTOCURRENCY":
        left = [
            ("Previous Close", _fmt_safe(info.get('previous_close'), "${:,.2f}")),
            ("Open", _fmt_safe(info.get('open_price'), "${:,.2f}")),
            ("Day's Range", _fmt_range(info.get('day_low'), info.get('day_high'))),
            ("52-Week Range", _fmt_range(info.get('fifty_two_week_low'), info.get('fifty_two_week_high'))),
        ]
        right = [
            ("Market Cap", _fmt_number(info.get('market_cap'), prefix="$")),
            ("Circulating Supply", _fmt_supply(info.get('circulating_supply'))),
            ("Max Supply", _fmt_supply(info.get('max_supply'))),
            ("Volume (24h)", _fmt_number(info.get('volume_24h'), prefix="$")),
        ]

    else:  # EQUITY (default)
        bid = info.get('bid')
        bid_size = info.get('bid_size')
        ask = info.get('ask')
        ask_size = info.get('ask_size')

        if bid and bid_size:
            bid_str = f"{bid:,.2f} x {int(bid_size):,}"
        elif bid:
            bid_str = f"${bid:,.2f}"
        else:
            bid_str = "N/A"

        if ask and ask_size:
            ask_str = f"{ask:,.2f} x {int(ask_size):,}"
        elif ask:
            ask_str = f"${ask:,.2f}"
        else:
            ask_str = "N/A"

        div_rate = info.get('dividend_rate')
        div_yield = info.get('dividend_yield')
        if div_rate is not None and div_yield is not None:
            fwd_div_str = f"{div_rate:.2f} ({div_yield * 100:.2f}%)"
        elif div_rate is not None:
            fwd_div_str = f"{div_rate:.2f}"
        elif div_yield is not None:
            fwd_div_str = f"{div_yield * 100:.2f}%"
        else:
            fwd_div_str = "N/A"

        left = [
            ("Previous Close", _fmt_safe(info.get('previous_close'), "${:,.2f}")),
            ("Open", _fmt_safe(info.get('open_price'), "${:,.2f}")),
            ("Bid", bid_str),
            ("Ask", ask_str),
            ("Day's Range", _fmt_range(info.get('day_low'), info.get('day_high'))),
            ("52 Week Range", _fmt_range(info.get('fifty_two_week_low'), info.get('fifty_two_week_high'))),
            ("Volume", _fmt_number(info.get('volume'))),
            ("Avg. Volume", _fmt_number(info.get('avg_volume'))),
        ]
        right = [
            ("Market Cap (intraday)", _fmt_number(info.get('market_cap'), prefix="$")),
            ("Beta (5Y Monthly)", _fmt_safe(info.get('beta'))),
            ("PE Ratio (TTM)", _fmt_safe(info.get('pe_ratio'))),
            ("EPS (TTM)", _fmt_safe(info.get('eps'), "${:,.2f}")),
            ("Earnings Date (est.)", _fmt_date(info.get('next_earnings_date'))),
            ("Forward Dividend & Yield", fwd_div_str),
            ("Ex-Dividend Date", _fmt_date(info.get('ex_dividend_date'))),
            ("1y Target Est", _fmt_safe(info.get('target_mean_price'), "${:,.2f}")),
        ]

    # Check if any data is actually available (not all N/A)
    all_items = left + right
    has_data = any(v != "N/A" for _, v in all_items)

    if not has_data:
        st.info("⏳ Market data is temporarily unavailable. This can happen due to rate limiting — please try again in a few seconds.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(_build_stat_table(left), unsafe_allow_html=True)
    with col2:
        st.markdown(_build_stat_table(right), unsafe_allow_html=True)


def _quarter_label(dt) -> str:
    """Convert a datetime to a calendar-quarter label like 'Q3 FY25'."""
    q = (dt.month - 1) // 3 + 1
    fy = dt.year % 100
    return f"Q{q} FY{fy:02d}"


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
        f'Trailing total returns as of {note_date}, which may include dividends or other distributions. '
        f'Benchmark is S&amp;P 500 (^GSPC).</div>',
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
                f'<div style="font-size:0.875rem;font-weight:600;color:#1E3A5F;margin-bottom:14px;">'
                f'{period_label}</div>'
                f'<div style="margin-bottom:12px;">'
                f'<div style="font-size:0.72rem;color:#64748B;margin-bottom:2px;">{ticker}</div>'
                f'<div style="font-size:1.9rem;font-weight:700;color:{t_color};">{t_str}</div>'
                f'</div>'
                f'<div style="border-top:1px solid #F1F5F9;padding-top:10px;">'
                f'<div style="font-size:0.72rem;color:#64748B;margin-bottom:2px;">S&amp;P 500 (^GSPC)</div>'
                f'<div style="font-size:1.3rem;font-weight:600;color:{s_color};">{s_str}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

def _render_revenue(fin_df: pd.DataFrame):
    """Render Revenue vs. Earnings tab — grouped bar chart by quarter."""

    if fin_df.empty:
        st.info("Revenue data is not available for this asset.")
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

    fig = go.Figure()
    if revenues:
        fig.add_trace(go.Bar(
            x=q_labels, y=_sc(revenues), name='Revenue',
            marker_color='#60A5FA',
            hovertemplate=f'Revenue: $%{{y:.2f}}{suffix}<extra></extra>',
        ))
    if net_incomes:
        fig.add_trace(go.Bar(
            x=q_labels, y=_sc(net_incomes), name='Earnings',
            marker_color='#F59E0B',
            hovertemplate=f'Earnings: $%{{y:.2f}}{suffix}<extra></extra>',
        ))

    fig.update_layout(
        barmode='group', height=300,
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=20, b=40),
        showlegend=True,
        legend=dict(orientation='h', y=1.12, x=0, xanchor='left', font=dict(size=11)),
        font=dict(family="Inter, sans-serif"),
        xaxis=dict(gridcolor='#E2E8F0'),
        yaxis=dict(
            gridcolor='#E2E8F0',
            tickprefix='$', ticksuffix=suffix, tickformat='.2f',
        )
    )
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': False})

def _render_fund_details(info):
    """Render Fund Details tab (ETFs only)."""
    items = [
        ("Fund Family", info.get('fund_family') or "N/A"),
        ("Net Assets", _fmt_number(info.get('net_assets'), prefix="$")),
        ("NAV", _fmt_safe(info.get('nav_price'), "${:,.2f}")),
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
        <p class="page-subtitle">Explore any stock, ETF, or index with real-time market data</p>
    </div>
    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # Search bar — empty by default, user must click 🔍
    # ═══════════════════════════════════════════════════════
    # Inject search bar styling — perfectly align search button with input
    st.markdown("""
    <style>
    /* Align bottom edges to account for label gap */
    [data-testid="stHorizontalBlock"] > div:has(button) {
        display: flex;
        align-items: flex-end;
    }
    /* Fine-tune button size to align perfectly with standard 40px input */
    [data-testid="stHorizontalBlock"] > div:has(button) button {
        height: 40px !important;
        min-height: 40px !important;
        padding: 0 !important;
        margin-bottom: 0px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_pad_l, col_input, col_search, col_pad_r = st.columns([0.5, 3, 0.4, 0.5])

    with col_input:
        ticker_input = st.text_input(
            "Ticker Symbol",
            value="",
            placeholder="e.g. GOOGL",
            help="Stocks, ETFs, crypto (BTC-USD), indices (^GSPC) — any Yahoo Finance symbol",
            label_visibility="collapsed",
        ).strip().upper()

    with col_search:
        search_clicked = st.button("🔍", type="primary", use_container_width=True)

    # Validate: reject multiple symbols (comma/space separated)
    _is_multi = len([t for t in ticker_input.replace(',', ' ').split() if t]) > 1

    # Track searched ticker in session state
    if search_clicked and ticker_input:
        if _is_multi:
            st.warning("⚠️ Please enter **one symbol at a time** (e.g. `AAPL`). This tool analyses a single asset.")
            st.session_state['stocks_ticker'] = None
        else:
            st.session_state['stocks_ticker'] = ticker_input
    elif 'stocks_ticker' not in st.session_state:
        st.session_state['stocks_ticker'] = None

    active_ticker = st.session_state.get('stocks_ticker')

    if not active_ticker:
        # Empty state — clean hint
        st.markdown("""
        <div style="text-align:center;padding:80px 20px;color:#94A3B8;">
            <div style="font-size:2.5rem;margin-bottom:8px;">🔍</div>
            <div style="font-size:1rem;font-weight:500;">Search for any stock</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ═══════════════════════════════════════════════════════
    # Fetch data
    # ═══════════════════════════════════════════════════════
    yf_period, yf_interval = PERIOD_MAP["1Y"]

    try:
        with st.spinner(f"Loading {active_ticker}..."):
            ohlcv = download_ohlcv(active_ticker, period=yf_period, interval=yf_interval)
            info = get_asset_info(active_ticker)
    except ValueError as e:
        st.error(f"❌ {e}")
        return
    except Exception as e:
        st.error(f"❌ Could not fetch data for **{active_ticker}**: {e}")
        return

    if ohlcv.empty:
        st.error(f"No data found for {active_ticker}")
        return

    # ═══════════════════════════════════════════════════════
    # Determine asset type
    # ═══════════════════════════════════════════════════════
    asset_type = (info.get('type') or 'EQUITY').upper()

    # ═══════════════════════════════════════════════════════
    # Price Header
    # ═══════════════════════════════════════════════════════
    price = info.get('price')
    prev_close = info.get('previous_close')
    name = info.get('name', active_ticker)
    sector = info.get('sector')
    industry = info.get('industry')

    if price and prev_close:
        change = price - prev_close
        change_pct = (change / prev_close) * 100
    else:
        change, change_pct = None, None

    # Sector/industry tag
    tag_html = ""
    if sector:
        tag_html = (
            f'<span style="background:#EFF6FF;color:#2E6FC7;padding:2px 10px;border-radius:12px;'
            f'font-size:0.75rem;font-weight:500;margin-left:12px;">{sector}'
            + (f' · {industry}' if industry else '')
            + '</span>'
        )
    elif asset_type == "ETF":
        fund_family = info.get('fund_family')
        tag_html = (
            f'<span style="background:#F0FDF4;color:#16A34A;padding:2px 10px;border-radius:12px;'
            f'font-size:0.75rem;font-weight:500;margin-left:12px;">ETF'
            + (f' · {fund_family}' if fund_family else '')
            + '</span>'
        )
    elif asset_type == "CRYPTOCURRENCY":
        tag_html = (
            '<span style="background:#FFF7ED;color:#EA580C;padding:2px 10px;border-radius:12px;'
            'font-size:0.75rem;font-weight:500;margin-left:12px;">Crypto</span>'
        )
    elif asset_type == "INDEX":
        tag_html = (
            '<span style="background:#F5F3FF;color:#7C3AED;padding:2px 10px;border-radius:12px;'
            'font-size:0.75rem;font-weight:500;margin-left:12px;">Index</span>'
        )

    if price:
        chg_str = ""
        if change is not None and change_pct is not None:
            chg_color = "#16A34A" if change >= 0 else "#DC2626"
            chg_sign = "+" if change >= 0 else ""
            chg_str = (
                f'<span style="color:{chg_color};font-size:1.1rem;margin-left:12px;">'
                f'{chg_sign}{change:.2f} ({chg_sign}{change_pct:.2f}%)</span>'
            )
        st.markdown(
            f'<div style="margin-bottom:0.3rem;">'
            f'<span style="font-size:1.3rem;font-weight:700;color:#1E3A5F;">{name}</span>'
            f'<span style="color:#64748B;margin-left:8px;">({active_ticker})</span>'
            f'{tag_html}'
            f'</div>'
            f'<div style="margin-bottom:0.8rem;">'
            f'<span style="font-size:2.2rem;font-weight:700;color:#0A1628;">${price:,.2f}</span>'
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
    if (yf_period, yf_interval) != PERIOD_MAP.get("1Y"):
        try:
            # Extended hours for 1D and 5D equity charts (not crypto).
            # Diagnostic confirmed 5D prepost data is clean: sorted, no zeros, no NaN, no >5% jumps.
            use_prepost = (period_label in ("1D", "5D")) and (asset_type != "CRYPTOCURRENCY")
            # For 5D: use start=today-5days (Yahoo Finance counts 120h back from now,
            # not 5 trading days from last close — avoids showing one extra day on weekends)
            if period_label == "5D":
                _start_5d = (_dt.datetime.now() - _dt.timedelta(days=5)).strftime("%Y-%m-%d")
                ohlcv = download_ohlcv(active_ticker, start=_start_5d,
                                       interval=yf_interval, prepost=use_prepost)
            else:
                ohlcv = download_ohlcv(active_ticker, period=yf_period,
                                       interval=yf_interval, prepost=use_prepost)
            if is_intraday and ohlcv.index.tz is not None:
                try:
                    ohlcv.index = ohlcv.index.tz_convert('America/New_York').tz_localize(None)
                except Exception:
                    ohlcv.index = ohlcv.index.tz_localize(None)
                
            # --- INTRADAY PADDING: fill empty bars up to market end ---
            if period_label == "1D" and not ohlcv.empty:
                last_ts = ohlcv.index[-1]
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
                        empty_df = pd.DataFrame(index=future_index, columns=ohlcv.columns)
                        ohlcv = pd.concat([ohlcv, empty_df])
        except Exception:
            pass

    st.plotly_chart(
        _create_price_chart(ohlcv, active_ticker, chart_type,
                            prev_close=info.get('previous_close'), is_intraday=is_intraday),
        width='stretch', config={'scrollZoom': False}
    )

    # ═══════════════════════════════════════════════════════
    # Period Returns Strip
    # Uses auto_adjust=False (split-adj, no dividend adj) + max history
    # to match Yahoo Finance return calculations exactly.
    # ═══════════════════════════════════════════════════════
    hist_close = pd.Series(dtype=float)
    try:
        hist_raw = download_ohlcv(active_ticker, period="max", interval="1d", auto_adjust=False)
        hist_close = hist_raw["Close"].squeeze().dropna()
        rets = _calculate_returns(hist_close, current_price=price)
    except Exception:
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
            pct_str = f"{val:+.2%}"
        else:
            color, pct_str = "#94A3B8", "—"
        cells += (
            '<div style="text-align:center;flex:1;min-width:38px;padding:6px 3px;">'
            f'<div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;white-space:nowrap;">{label}</div>'
            f'<div style="font-size:0.78rem;font-weight:600;color:{color};white-space:nowrap;">{pct_str}</div>'
            '</div>'
        )
    st.markdown(
        '<div style="display:flex;flex-wrap:wrap;border:1px solid #E2E8F0;border-radius:8px;'
        f'background:white;margin:0.5rem 0 1rem 0;">{cells}</div>',
        unsafe_allow_html=True
    )

    # ═══════════════════════════════════════════════════════
    # Additional data for EQUITY tabs (cached — fast on re-render)
    # ═══════════════════════════════════════════════════════
    spy_close = pd.Series(dtype=float)
    quarterly_fin_df = pd.DataFrame()

    if asset_type == "EQUITY":
        try:
            _spy_raw = download_ohlcv('^GSPC', period='max', interval='1d', auto_adjust=False)
            spy_close = _spy_raw['Close'].squeeze().dropna()
        except Exception:
            pass
        try:
            quarterly_fin_df = get_quarterly_financials(active_ticker)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # Adaptive Tabs
    # ═══════════════════════════════════════════════════════

    if asset_type == "EQUITY":
        tab_stats, tab_perf, tab_rev = st.tabs([
            "📊 Key Statistics", "📈 Performance", "📑 Revenue vs. Earnings",
        ])
        with tab_stats:
            _render_key_stats(info, asset_type)
        with tab_perf:
            _render_performance(active_ticker, hist_close, price, spy_close)
        with tab_rev:
            _render_revenue(quarterly_fin_df)

    elif asset_type == "ETF":
        tab_stats, tab_fund = st.tabs(["📊 Market Data", "🏦 Fund Details"])
        with tab_stats:
            _render_key_stats(info, asset_type)
        with tab_fund:
            _render_fund_details(info)

    elif asset_type == "CRYPTOCURRENCY":
        tab_stats, = st.tabs(["📊 Market & Supply"])
        with tab_stats:
            _render_key_stats(info, asset_type)

    elif asset_type == "INDEX":
        tab_stats, = st.tabs(["📊 Market Data"])
        with tab_stats:
            _render_key_stats(info, asset_type)

    else:
        # Unknown type — show basic overview
        tab_stats, = st.tabs(["📊 Overview"])
        with tab_stats:
            _render_key_stats(info, "EQUITY")


    # ── Render Footer ──
    from utils.styles import render_footer
    render_footer()

if __name__ == "__main__":
    main()
