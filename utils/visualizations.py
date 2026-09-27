"""
Visualization utilities for Black-Litterman Portfolio Optimizer
Creates interactive charts using Plotly
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import yfinance as yf

from core.constants import ASSET_COLORS, MIN_WEIGHT_THRESHOLD, TRADING_DAYS_PER_YEAR


# ── Brand chart style ──
# Shared by every interactive chart (Portfolio results and the Stocks page; the
# Home page draws those same charts on example data): Inter for text and
# figures (the page CSS gives chart text same-width digits), a faint navy
# grid, a navy hover label. The fonts are loaded by the page CSS
# (utils/styles.py). The PDF charts are matplotlib and keep their own style
# (core/pdf_shared.py).
BRAND_FONT = "Inter, sans-serif"
BRAND_DISPLAY = "DM Sans, Inter, sans-serif"
BRAND_INK = "#0A1628"
BRAND_MUTED = "#64748B"
BRAND_GRID = "rgba(10, 22, 40, 0.08)"
BRAND_ZERO = "rgba(10, 22, 40, 0.20)"
# Asset colors (core/constants.py, shared with the PDF)
BRAND_SEQUENCE = ASSET_COLORS
# A donut reads well up to six slices; with more, slices get too thin to
# compare and the allocation is drawn as bars (create_allocation_chart).
MAX_DONUT_SLICES = 6


def apply_brand_layout(fig: go.Figure, axes: bool = True) -> go.Figure:
    """
    Apply the shared brand style to a Plotly figure, in place.

    Only fonts, grid lines and the hover label change. Trace colors and
    chart-specific axis settings (ranges, suffixes, formats) are left alone.

    Args:
        fig: Figure to style.
        axes: Also style the cartesian axes. False for charts without them (pie).

    Returns:
        The same figure, so builders can `return apply_brand_layout(fig)`.
    """
    fig.update_layout(
        font=dict(family=BRAND_FONT, color=BRAND_INK),
        hoverlabel=dict(
            bgcolor=BRAND_INK,
            bordercolor=BRAND_INK,
            font=dict(family=BRAND_FONT, size=12, color="#FFFFFF"),
        ),
    )
    # Only for figures that have a title: a title object without text makes
    # the chart print "undefined" in its top-left corner.
    if fig.layout.title.text:
        fig.update_layout(title_font_family=BRAND_DISPLAY)
    if axes:
        axis_style = dict(
            gridcolor=BRAND_GRID,
            zerolinecolor=BRAND_ZERO,
            tickfont=dict(family=BRAND_FONT, size=11, color=BRAND_MUTED),
        )
        fig.update_xaxes(**axis_style)
        fig.update_yaxes(**axis_style)
    return fig


def create_correlation_heatmap(cov_matrix: np.ndarray, tickers: list) -> go.Figure:
    """
    Create correlation matrix heatmap.

    Args:
        cov_matrix: Covariance matrix
        tickers: Ticker symbols in the matrix's own row order (the result's
            'covariance_tickers'); any other order mislabels the cells

    Returns:
        Plotly figure object
    """
    # Convert covariance to correlation
    std_devs = np.sqrt(np.diag(cov_matrix))
    corr_matrix = cov_matrix / np.outer(std_devs, std_devs)

    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix,
        x=tickers,
        y=tickers,
        colorscale='RdBu',
        zmid=0,
        text=np.round(corr_matrix, 2),
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="Correlation")
    ))

    fig.update_layout(
        xaxis_title='',
        yaxis_title='',
        height=500,
        margin=dict(t=20, b=40, l=60, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    return apply_brand_layout(fig)


def create_returns_comparison(
    market_prior: Dict[str, float],
    posterior: Dict[str, float],
    views: Optional[Dict[str, float]] = None
) -> go.Figure:
    """
    Create bar chart comparing market prior, views, and posterior returns.

    Args:
        market_prior: Market-implied prior returns
        posterior: Black-Litterman posterior returns
        views: Optional user views

    Returns:
        Plotly figure object
    """
    tickers = list(market_prior.keys())

    # Prepare data
    data = []

    # Market Prior
    data.append(go.Bar(
        name='Market Prior',
        x=tickers,
        y=[market_prior[t] * 100 for t in tickers],
        marker_color='#2E6FC7'  # Primary Blue
    ))

    # User Views (if provided). Assets without a view get no bar: a zero
    # bar would read as a view of 0%.
    if views:
        data.append(go.Bar(
            name='Your Views',
            x=tickers,
            y=[views[t] * 100 if t in views else None for t in tickers],
            marker_color='#F59E0B'  # Warning Amber
        ))

    # Posterior
    data.append(go.Bar(
        name='Posterior (BL)',
        x=tickers,
        y=[posterior[t] * 100 for t in tickers],
        marker_color='#10B981'  # Success Green
    ))

    fig = go.Figure(data=data)

    fig.update_layout(
        xaxis_title='Asset',
        yaxis_title='Expected Annual Return (%)',
        barmode='group',
        height=500,
        margin=dict(t=50, b=60, l=60, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return apply_brand_layout(fig)


def create_allocation_pie(weights: Dict[str, float], min_weight: float = MIN_WEIGHT_THRESHOLD) -> go.Figure:
    """
    Create pie chart for portfolio allocation.

    Args:
        weights: Portfolio weights dictionary
        min_weight: Minimum weight threshold to display

    Returns:
        Plotly figure object
    """
    # Filter out very small weights
    filtered_weights = {k: v for k, v in weights.items() if v > min_weight}

    if not filtered_weights:
        # Return empty figure if no significant weights
        fig = go.Figure()
        fig.add_annotation(
            text="No significant allocations",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        return fig

    tickers = list(filtered_weights.keys())
    values = [filtered_weights[t] * 100 for t in tickers]

    # Brand asset palette (BRAND_SEQUENCE covers MAX_TICKERS)
    corporate_colors = BRAND_SEQUENCE[:len(tickers)]

    fig = go.Figure(data=[go.Pie(
        labels=tickers,
        values=values,
        hole=0.55,
        # Each slice is labeled directly, so there is no legend to look up
        textinfo='label+percent',
        textfont_size=12,
        # Small slices get their label outside the pie: let it widen the
        # margins instead of being cut off at the chart's edge
        automargin=True,
        hovertemplate='<b>%{label}</b><br>Weight: %{percent}<extra></extra>',
        marker=dict(
            colors=corporate_colors,
            line=dict(color='#FFFFFF', width=2)
        )
    )])

    fig.update_layout(
        height=500,
        margin=dict(t=20, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        annotations=[dict(
            text=f"{len(tickers)}<br>{'asset' if len(tickers) == 1 else 'assets'}",
            showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper",
            font=dict(size=15, color=BRAND_MUTED),
        )],
    )

    return apply_brand_layout(fig, axes=False)


def create_allocation_bars(weights: Dict[str, float], min_weight: float = MIN_WEIGHT_THRESHOLD) -> go.Figure:
    """
    Horizontal bars of the portfolio weights, largest at the top.

    For portfolios with more slices than a donut shows clearly
    (create_allocation_chart picks).

    Args:
        weights: Portfolio weights dictionary
        min_weight: Minimum weight threshold to display

    Returns:
        Plotly figure object
    """
    shown = sorted(((t, w) for t, w in weights.items() if w > min_weight), key=lambda x: x[1])
    tickers = [t for t, _ in shown]
    values = [w * 100 for _, w in shown]

    fig = go.Figure(go.Bar(
        x=values,
        y=tickers,
        orientation='h',
        marker_color='#2E6FC7',
        text=[f"{v:.1f}%" for v in values],
        textposition='outside',
        cliponaxis=False,
        hovertemplate='<b>%{y}</b><br>Weight: %{x:.2f}%<extra></extra>',
    ))

    fig.update_layout(
        height=max(300, 34 * len(tickers) + 60),
        margin=dict(t=10, b=30, l=10, r=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        bargap=0.35,
        xaxis=dict(ticksuffix='%', rangemode='tozero'),
    )

    apply_brand_layout(fig)
    fig.update_yaxes(showgrid=False)
    return fig


def create_allocation_chart(weights: Dict[str, float], min_weight: float = MIN_WEIGHT_THRESHOLD) -> go.Figure:
    """
    The Allocation tab's chart: a donut for up to MAX_DONUT_SLICES assets,
    horizontal bars beyond that.

    Args:
        weights: Portfolio weights dictionary
        min_weight: Minimum weight threshold to display

    Returns:
        Plotly figure object
    """
    shown = sum(1 for w in weights.values() if w > min_weight)
    if shown > MAX_DONUT_SLICES:
        return create_allocation_bars(weights, min_weight)
    return create_allocation_pie(weights, min_weight)


def create_price_chart(ohlcv, ticker, chart_type, prev_close=None, is_intraday=False):
    """
    Price chart of the Stocks page: price (line or candles) over volume.

    The Home page's Stocks card draws it too, on example data, so the
    picture there is exactly what the Stocks page shows.
    """
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
        "<b>%{customdata[0]}</b><br>"
        "Close: %{customdata[1]}<br>"
        "Open: %{customdata[2]}<br>"
        "High: %{customdata[3]}<br>"
        "Low: %{customdata[4]}<br>"
        "Volume: %{customdata[5]}"
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
    )

    if prev_close and is_intraday:
        fig.add_hline(
            y=prev_close, line_dash="dash", line_color="#94A3B8", line_width=1, row=1, col=1,
            annotation_text=f"Prev Close {prev_close:,.2f}",
            annotation_position="right", annotation_font_color="#94A3B8", annotation_font_size=10,
        )

    apply_brand_layout(fig)
    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(showgrid=True)

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


def create_efficient_frontier_chart(ef_data: dict, selected_portfolio: dict = None) -> go.Figure:
    """
    Create efficient frontier visualization with key portfolio markers.

    Args:
        ef_data: Dictionary containing mus, sigmas, optimal returns/risks, min vol, and asset details
        selected_portfolio: Optional dict with 'ret', 'risk', 'sharpe', 'label' for the user's chosen portfolio

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    # 1. Efficient Frontier Curve
    if ef_data.get('mus') and ef_data.get('sigmas'):
        mus_pct = [m * 100 for m in ef_data['mus']]
        sigmas_pct = [s * 100 for s in ef_data['sigmas']]
        
        fig.add_trace(go.Scatter(
            x=sigmas_pct,
            y=mus_pct,
            mode='lines',
            line=dict(color='#2E6FC7', width=3),
            name='Efficient Frontier',
            hovertemplate='Volatility: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>'
        ))

    # 2. Individual Assets
    if ef_data.get('asset_mu') and ef_data.get('asset_sigma'):
        asset_names = list(ef_data['asset_mu'].keys())
        a_mu = [ef_data['asset_mu'][a] * 100 for a in asset_names]
        a_sig = [ef_data['asset_sigma'][a] * 100 for a in asset_names]
        
        fig.add_trace(go.Scatter(
            x=a_sig,
            y=a_mu,
            mode='markers+text',
            marker=dict(size=10, symbol='star-diamond', color='#94A3B8', line=dict(color='#FFFFFF', width=1)),
            name='Individual Assets',
            text=asset_names,
            textposition='top center',
            textfont=dict(size=10, color='#64748B'),
            hovertemplate='<b>%{text}</b><br>Volatility: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>'
        ))

    # 3. Max Sharpe Portfolio (reference marker)
    if ef_data.get('optimal_ret') is not None and ef_data.get('optimal_risk') is not None:
        opt_ret = ef_data['optimal_ret'] * 100
        opt_risk = ef_data['optimal_risk'] * 100
        sharpe = ef_data.get('sharpe_max', 0)
        
        fig.add_trace(go.Scatter(
            x=[opt_risk],
            y=[opt_ret],
            mode='markers',
            marker=dict(size=14, symbol='circle', color='#10B981', line=dict(color='#FFFFFF', width=2)),
            name='Max Sharpe',
            text=[f"Sharpe: {sharpe:.2f}"],
            hovertemplate='<b>Max Sharpe</b><br>%{text}<br>Volatility: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>'
        ))

    # 4. Min Volatility Portfolio (reference marker)
    if ef_data.get('min_vol_ret') is not None and ef_data.get('min_vol_risk') is not None:
        mv_ret = ef_data['min_vol_ret'] * 100
        mv_risk = ef_data['min_vol_risk'] * 100
        
        fig.add_trace(go.Scatter(
            x=[mv_risk],
            y=[mv_ret],
            mode='markers',
            marker=dict(size=14, symbol='diamond', color='#2E6FC7', line=dict(color='#FFFFFF', width=2)),
            name='Min Variance',
            hovertemplate='<b>Min Variance</b><br>Volatility: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>'
        ))

    # 5. Selected Portfolio (user's actual result — amber marker)
    if selected_portfolio:
        sel_ret = selected_portfolio['ret'] * 100
        sel_risk = selected_portfolio['risk'] * 100
        sel_label = selected_portfolio.get('label', 'Portfolio')
        sel_sharpe = selected_portfolio.get('sharpe', 0)
        
        fig.add_trace(go.Scatter(
            x=[sel_risk],
            y=[sel_ret],
            mode='markers',
            marker=dict(size=10, symbol='star-diamond', color='#F59E0B', line=dict(color='#FFFFFF', width=2)),
            name=sel_label,
            text=[f"Sharpe: {sel_sharpe:.2f}"],
            hovertemplate=f'<b>{sel_label}</b><br>%{{text}}<br>Volatility: %{{x:.2f}}%<br>Return: %{{y:.2f}}%<extra></extra>'
        ))

    fig.update_layout(
        xaxis_title='Volatility (Annual %)',
        yaxis_title='Expected Return (Annual %)',
        height=500,
        width=800,
        margin=dict(t=60, b=60, l=60, r=60),
        hovermode='closest',
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(ticksuffix='%'),
        yaxis=dict(ticksuffix='%'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )

    return apply_brand_layout(fig)


def create_risk_return_scatter(
    weights: Dict[str, float],
    returns: Dict[str, float],
    volatilities: Dict[str, float]
) -> go.Figure:
    """
    Create risk-return scatter plot for individual assets.

    Args:
        weights: Portfolio weights
        returns: Expected returns for each asset
        volatilities: Volatility for each asset

    Returns:
        Plotly figure object
    """
    tickers = list(weights.keys())

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=[volatilities[t] * 100 for t in tickers],
        y=[returns[t] * 100 for t in tickers],
        mode='markers+text',
        marker=dict(
            size=[weights[t] * 1000 for t in tickers],  # Size proportional to weight
            color=[weights[t] * 100 for t in tickers],
            colorscale='Blues',
            showscale=True,
            colorbar=dict(title="Weight (%)"),
            line=dict(color='white', width=1)
        ),
        text=tickers,
        textposition='top center',
        textfont=dict(size=10, family="Inter, sans-serif", color="#0A1628"),
        hovertemplate='<b>%{text}</b><br>' +
                      'Expected Return: %{y:.1f}%<br>' +
                      'Volatility: %{x:.1f}%<br>' +
                      '<extra></extra>'
    ))

    fig.update_layout(
        title='Risk-Return Profile by Asset',
        xaxis_title='Volatility (Annual %)',
        yaxis_title='Expected Return (Annual %)',
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False
    )

    return apply_brand_layout(fig)


def create_allocation_table(
    weights: Dict[str, float],
    allocation: Dict[str, int],
    prices: Dict[str, float],
    portfolio_value: float
) -> pd.DataFrame:
    """
    Create allocation summary table.

    Args:
        weights: Portfolio weights
        allocation: Discrete share allocation
        prices: Current prices
        portfolio_value: Total portfolio value

    Returns:
        Pandas DataFrame with allocation details
    """
    data = []

    for ticker in weights.keys():
        if weights[ticker] > MIN_WEIGHT_THRESHOLD:
            shares = allocation.get(ticker, 0)
            price = prices.get(ticker, 0)
            target_value = weights[ticker] * portfolio_value
            actual_value = shares * price if shares > 0 else 0

            data.append({
                'Asset': ticker,
                'Weight (%)': f"{weights[ticker] * 100:.2f}",
                'Target Value ($)': f"{target_value:,.2f}",
                'Shares': shares,
                'Price ($)': f"{price:.2f}",
                'Actual Value ($)': f"{actual_value:,.2f}"
            })

    df = pd.DataFrame(data)
    return df


def create_metrics_card_html(
    expected_return: float,
    volatility: float,
    sharpe_ratio: float,
    portfolio_value: float,
    num_assets: int
) -> str:
    """
    Create HTML for metrics summary cards.

    Args:
        expected_return: Expected annual return
        volatility: Annual volatility
        sharpe_ratio: Sharpe ratio
        portfolio_value: Total portfolio value
        num_assets: Number of assets in portfolio

    Returns:
        HTML string
    """
    html = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 2rem 0; font-family: Inter, sans-serif;">
        <div style="background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(226, 232, 240, 0.8); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-left: 3px solid #10B981;">
            <div style="font-size: 0.85rem; color: #64748B; margin-bottom: 0.5rem; font-weight: 500;">Expected Return</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #10B981;">{expected_return*100:.2f}%</div>
        </div>

        <div style="background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(226, 232, 240, 0.8); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-left: 3px solid #F59E0B;">
            <div style="font-size: 0.85rem; color: #64748B; margin-bottom: 0.5rem; font-weight: 500;">Volatility</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #F59E0B;">{volatility*100:.2f}%</div>
        </div>

        <div style="background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(226, 232, 240, 0.8); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-left: 3px solid #2E6FC7;">
            <div style="font-size: 0.85rem; color: #64748B; margin-bottom: 0.5rem; font-weight: 500;">Sharpe Ratio</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #2E6FC7;">{sharpe_ratio:.3f}</div>
        </div>

        <div style="background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(226, 232, 240, 0.8); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-left: 3px solid #0A1628;">
            <div style="font-size: 0.85rem; color: #64748B; margin-bottom: 0.5rem; font-weight: 500;">Portfolio Value</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #0A1628;">${portfolio_value:,.0f}</div>
        </div>

        <div style="background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(226, 232, 240, 0.8); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-left: 3px solid #334155;">
            <div style="font-size: 0.85rem; color: #64748B; margin-bottom: 0.5rem; font-weight: 500;">Assets</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #0A1628;">{num_assets}</div>
        </div>
    </div>
    """
    return html


def create_historical_performance_chart(
    weights: Dict[str, float],
    tickers: List[str],
    portfolio_value: float,
    benchmark: str = 'SPY',
    initial_date: Optional[str] = None,
    prices_data: Optional[pd.DataFrame] = None,
    period: str = "All",
    model_type: str = "Black-Litterman",
) -> tuple:
    """
    Create interactive historical performance comparison chart.

    Data calculations are delegated to core.backtest (single source of truth).
    Returns are REBASED to 0% at the start of the selected period so that
    1D, 5D, 1M, etc. all show meaningful relative performance.

    Args:
        weights: Portfolio weights dictionary
        tickers: List of ticker symbols
        portfolio_value: Initial portfolio value
        benchmark: Benchmark ticker (default: SPY for S&P 500)
        initial_date: Optional start date for the backtest
        prices_data: Optional pre-downloaded price DataFrame.
        period: Time window to display. One of: 1D, 5D, 1M, 6M, YTD, 1Y, 5Y, All.

    Returns:
        Tuple of (Plotly figure, BacktestResult or None).
        The BacktestResult contains annualized metrics for both portfolio and benchmark.
    """
    from core.backtest import run_backtest as _core_backtest

    try:
        # ── Step 1: Prepare price data ──
        price_df = _prepare_price_data(
            tickers=tickers,
            benchmark=benchmark,
            initial_date=initial_date,
            prices_data=prices_data,
        )

        # ── Step 2: Run unified backtest ──
        bt_result = _core_backtest(
            prices=price_df,
            weights=weights,
            tickers=tickers,
            portfolio_value=portfolio_value,
            benchmark_col=benchmark,
            min_data_points=20,
        )

        if bt_result is None:
            raise ValueError("Insufficient data for backtest (need at least 20 common dates)")

        # ── Step 3: Build Plotly chart from backtest result ──
        #
        # The caller passes `period` to select which time window to show.
        # Returns are REBASED to 0% at the start of the selected window so
        # that 1D, 5D, 1M etc. all show meaningful relative performance.
        dates = pd.to_datetime(bt_result.dates)

        values_df = pd.DataFrame({
            'date': dates,
            'portfolio': bt_result.portfolio_values,
            'benchmark': bt_result.benchmark_values,
        }).set_index('date')

        # Determine the start date for the selected period
        from dateutil.relativedelta import relativedelta

        last_date = values_df.index[-1]
        period_map = {
            "1M":  last_date - relativedelta(months=1),
            "6M":  last_date - relativedelta(months=6),
            "YTD": pd.Timestamp(last_date.year, 1, 1),
            "1Y":  last_date - relativedelta(years=1),
            "5Y":  last_date - relativedelta(years=5),
            "All": values_df.index[0],
        }

        period_start = period_map.get(period, values_df.index[0])
        subset = values_df.loc[values_df.index >= period_start]
        if len(subset) < 2:
            subset = values_df.iloc[-2:]

        # Rebase returns to 0% at the start of this window
        p_pct = ((subset['portfolio'] / subset['portfolio'].iloc[0]) - 1) * 100
        b_pct = ((subset['benchmark'] / subset['benchmark'].iloc[0]) - 1) * 100

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=subset.index,
            y=p_pct,
            mode='lines',
            name=f'{model_type} Portfolio',
            line=dict(color='#2E6FC7', width=2.5), # Primary Blue
            hovertemplate='<b>Portfolio</b><br>Date: %{x}<br>Return: %{y:.2f}%<extra></extra>'
        ))

        fig.add_trace(go.Scatter(
            x=subset.index,
            y=b_pct,
            mode='lines',
            name=f'{benchmark} Benchmark',
            line=dict(color='#64748B', width=2, dash='dash'), # Gray
            hovertemplate=f'<b>{benchmark}</b><br>Date: %{{x}}<br>Return: %{{y:.2f}}%<extra></extra>'
        ))

        # Summary annotation: returns over the window on screen. (Dollar
        # values would start from the full period's first day, not the
        # window's, so they are left out.)
        p_ret = p_pct.iloc[-1]
        b_ret = b_pct.iloc[-1]
        summary = (f'{subset.index[0]:%Y-%m-%d} to {subset.index[-1]:%Y-%m-%d}: '
                   f'Portfolio {p_ret:+.2f}% | {benchmark} {b_ret:+.2f}%')

        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Cumulative Return (%)',
            height=600,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                xanchor="right",
                x=1
            ),
            margin=dict(t=50, b=120, l=60, r=40),
            yaxis=dict(
                ticksuffix='%',
                tickformat=',.0f'
            ),
            xaxis=dict(
                type="date",
            ),
            annotations=[dict(
                text=summary,
                xref="paper", yref="paper",
                x=0.5, y=-0.18,
                showarrow=False,
                font=dict(family=BRAND_FONT, size=12, color="#64748B"),
                xanchor='center'
            )]
        )

        return apply_brand_layout(fig), bt_result

    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(
            text=f"Could not load historical data: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color='red')
        )
        fig.update_layout(height=400)
        return fig, None


def _prepare_price_data(
    tickers: List[str],
    benchmark: str = 'SPY',
    initial_date: Optional[str] = None,
    prices_data: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Prepare a clean DataFrame with ticker + benchmark columns for backtest.

    Reuses pre-downloaded data when available, downloads from yfinance otherwise.
    """
    if initial_date:
        start_date = pd.to_datetime(initial_date)
    else:
        start_date = datetime.now() - timedelta(days=365 * 5)
    end_date = datetime.now()

    # Try to use pre-downloaded data
    if prices_data is not None:
        available_tickers = [t for t in tickers if t in prices_data.columns]
        if len(available_tickers) == len(tickers):
            price_df = prices_data[tickers].copy()
            if initial_date:
                price_df = price_df.loc[price_df.index >= start_date]

            # Add benchmark
            if benchmark in prices_data.columns:
                price_df[benchmark] = prices_data[benchmark]
                if initial_date:
                    price_df = price_df.loc[price_df.index >= start_date]
            else:
                # Download just the benchmark via unified data provider
                from core.data_provider import download_prices
                start_str = start_date.strftime('%Y-%m-%d') if isinstance(start_date, (datetime, pd.Timestamp)) else str(start_date)
                end_str = end_date.strftime('%Y-%m-%d') if isinstance(end_date, (datetime, pd.Timestamp)) else str(end_date)
                bench_df = download_prices([benchmark], start=start_str, end=end_str)
                price_df[benchmark] = bench_df[benchmark]

            # The same rows the PDF backtests (core.backtest.prepare_backtest_prices)
            from core.backtest import prepare_backtest_prices
            return prepare_backtest_prices(price_df, tickers, benchmark)

    # Fallback: download everything via unified data provider
    from core.data_provider import download_prices

    all_tickers = list(set(tickers + [benchmark]))
    return download_prices(
        all_tickers,
        start=start_date.strftime('%Y-%m-%d') if isinstance(start_date, (datetime, pd.Timestamp)) else str(start_date),
        end=end_date.strftime('%Y-%m-%d') if isinstance(end_date, (datetime, pd.Timestamp)) else str(end_date),
    )
