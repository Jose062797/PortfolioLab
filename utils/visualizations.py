"""
Visualization utilities for Black-Litterman Portfolio Optimizer
Creates interactive charts using Plotly
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import yfinance as yf

from core.constants import MIN_WEIGHT_THRESHOLD, TRADING_DAYS_PER_YEAR


def create_correlation_heatmap(cov_matrix: np.ndarray, tickers: list) -> go.Figure:
    """
    Create correlation matrix heatmap.

    Args:
        cov_matrix: Covariance matrix
        tickers: List of ticker symbols

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
        title='Asset Correlation Matrix',
        xaxis_title='',
        yaxis_title='',
        height=500,
        font=dict(family="Inter, sans-serif", color="#0A1628"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        dragmode=False,
    )

    return fig


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

    # User Views (if provided)
    if views:
        data.append(go.Bar(
            name='Your Views',
            x=tickers,
            y=[views.get(t, 0) * 100 for t in tickers],
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
        title='Expected Returns Comparison',
        xaxis_title='Asset',
        yaxis_title='Expected Annual Return (%)',
        barmode='group',
        height=500,
        font=dict(family="Inter, sans-serif", color="#0A1628"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        dragmode=False,
    )

    return fig


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

    # Corporate color sequence
    corporate_colors = px.colors.qualitative.Pastel[:len(tickers)]

    fig = go.Figure(data=[go.Pie(
        labels=tickers,
        values=values,
        hole=0.3,
        textinfo='label+percent',
        textfont_size=12,
        marker=dict(
            colors=corporate_colors,
            line=dict(color='#FFFFFF', width=2)
        )
    )])

    fig.update_layout(
        title='Portfolio Allocation',
        height=500,
        font=dict(family="Inter, sans-serif", color="#0A1628"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        dragmode=False,
    )

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
            marker=dict(size=14, symbol='diamond', color='#3B82F6', line=dict(color='#FFFFFF', width=2)),
            name='Min Variance',
            hovertemplate='<b>Min Variance</b><br>Volatility: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>'
        ))

    # 5. Selected Portfolio (user's actual result — green marker)
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
        font=dict(family="Inter, sans-serif", color="#0A1628"),
        hovermode='closest',
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor='#E2E8F0', ticksuffix='%'),
        yaxis=dict(gridcolor='#E2E8F0', ticksuffix='%'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        dragmode=False,
    )

    return fig


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
        font=dict(family="Inter, sans-serif", color="#0A1628"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        dragmode=False,
    )

    return fig


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

        # Summary annotation
        p_ret = p_pct.iloc[-1]
        b_ret = b_pct.iloc[-1]
        p_final = subset['portfolio'].iloc[-1]
        b_final = subset['benchmark'].iloc[-1]
        summary = f'Portfolio: ${p_final:,.0f} ({p_ret:+.2f}%) | {benchmark}: ${b_final:,.0f} ({b_ret:+.2f}%)'

        fig.update_layout(
            title=dict(
                text=f'Historical Performance vs {benchmark} Benchmark',
                font=dict(size=18, family="Inter, sans-serif", color="#0A1628"),
                x=0.5,
                xanchor='center',
                y=0.98,
                yanchor='top'
            ),
            xaxis_title='Date',
            yaxis_title='Cumulative Return (%)',
            height=600,
            font=dict(family="Inter, sans-serif", color="#0A1628"),
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
            margin=dict(t=100, b=120, l=60, r=40),
            yaxis=dict(
                gridcolor='#E2E8F0',
                ticksuffix='%',
                tickformat=',.0f'
            ),
            xaxis=dict(
                gridcolor='#E2E8F0',
                type="date",
            ),
            annotations=[dict(
                text=summary,
                xref="paper", yref="paper",
                x=0.5, y=-0.18,
                showarrow=False,
                font=dict(size=12, color="#64748B"),
                xanchor='center'
            )],
            dragmode=False,
        )

        return fig, bt_result

    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(
            text=f"Could not load historical data: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color='red')
        )
        fig.update_layout(height=400, dragmode=False)
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

            return price_df.dropna()

    # Fallback: download everything via unified data provider
    from core.data_provider import download_prices

    all_tickers = list(set(tickers + [benchmark]))
    return download_prices(
        all_tickers,
        start=start_date.strftime('%Y-%m-%d') if isinstance(start_date, (datetime, pd.Timestamp)) else str(start_date),
        end=end_date.strftime('%Y-%m-%d') if isinstance(end_date, (datetime, pd.Timestamp)) else str(end_date),
    )
