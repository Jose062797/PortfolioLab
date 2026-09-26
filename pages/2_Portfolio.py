"""
Portfolio Page - Black-Litterman Streamlit App
Modern layout: no sidebar, top navbar, clean card-based UI
"""

import logging
import os
import io
import re
from datetime import datetime, timedelta

import utils.ssl_fix  # noqa: F401 — applies SSL cert fix on import

import streamlit as st
import pandas as pd
import numpy as np

from utils.session_manager import init_session_state, save_config, save_result, get_result, get_history
from utils.optimizer_wrapper import run_optimization, find_highly_correlated_pairs
from core.constants import MIN_WEIGHT_THRESHOLD
from utils.visualizations import (
    create_correlation_heatmap,
    create_returns_comparison,
    create_allocation_pie,
    create_allocation_table,
    create_efficient_frontier_chart,
    create_historical_performance_chart
)

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Portfolio · PortfolioLab",
    page_icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "favicon.png"),
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Critical CSS: hide sidebar/chrome IMMEDIATELY to prevent flash on navigation
from utils.styles import inject_critical_css, inject_styles, render_navbar
inject_critical_css()
inject_styles()
render_navbar(active_page="portfolio")

# Initialize session state
init_session_state()

# Initialize checkbox states if not present
if 'add_views_checkbox' not in st.session_state:
    st.session_state.add_views_checkbox = False
if 'use_date_range_checkbox' not in st.session_state:
    st.session_state.use_date_range_checkbox = False


def _apply_pending_restore():
    """Apply a pending history restore BEFORE any widgets are created.
    
    This avoids the StreamlitAPIException that occurs when modifying
    session_state keys (like 'tickers_input') after their associated
    widgets have already been instantiated in the current script run.
    """
    if '_pending_restore' not in st.session_state:
        return
    
    h_result = st.session_state.pop('_pending_restore')
    
    # Restore tickers
    if 'tickers' in h_result:
        st.session_state['tickers_input'] = ", ".join(h_result['tickers'])
    
    # Restore portfolio value
    if 'portfolio_value' in h_result:
        st.session_state['portfolio_value'] = h_result['portfolio_value']
    
    # Restore views
    if h_result.get('model_type') == 'Black-Litterman':
        st.session_state['add_views_checkbox'] = True
        views_to_restore = h_result.get('views_detail', {})
        if not views_to_restore:
            vd = h_result.get('viewdict', {})
            views_to_restore = {t: {'expected': v, 'lower': v - 0.05, 'upper': v + 0.05}
                                for t, v in vd.items()}
        if views_to_restore:
            st.session_state['selected_views_ms'] = list(views_to_restore.keys())
            for ticker, view_data in views_to_restore.items():
                if isinstance(view_data, dict):
                    st.session_state[f"exp_{ticker}"] = view_data.get(
                        'expected', view_data.get('expected_return', 0))
                    st.session_state[f"low_{ticker}"] = view_data.get('lower', 0)
                    st.session_state[f"upp_{ticker}"] = view_data.get('upper', 0)
                else:
                    st.session_state[f"exp_{ticker}"] = view_data
                    st.session_state[f"low_{ticker}"] = view_data - 0.05
                    st.session_state[f"upp_{ticker}"] = view_data + 0.05
    else:
        st.session_state['add_views_checkbox'] = False
        st.session_state['selected_views_ms'] = []

    # Restore model type
    if 'model_type' in h_result:
        model_options = ["Black-Litterman", "Markowitz"]
        if h_result['model_type'] in model_options:
            st.session_state['model_type_select'] = h_result['model_type']

    # Restore Markowitz objective (only relevant when model is Markowitz)
    if h_result.get('model_type') == 'Markowitz' and 'obj_function' in h_result:
        obj_options = ["Min Variance", "Max Sharpe",
                       "Maximise Return for a Given Risk", "Minimise Risk for a Given Return"]
        if h_result['obj_function'] in obj_options:
            st.session_state['obj_function_select'] = h_result['obj_function']


def main():
    """Main optimizer page - modern, clean layout."""


    # ── Page Header ──
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <p class="bl-eyebrow">Black-Litterman · Markowitz</p>
        <h1 class="page-title">Portfolio</h1>
        <p class="page-subtitle">Optimize a portfolio with Black-Litterman or Markowitz on market data from Yahoo Finance</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Configuration Section ──
    col1, spacer, col2 = st.columns([1, 0.08, 1])

    with col1:
        st.markdown("""
        <div class="step-header">
            <div class="step-circle blue">1</div>
            <span class="step-title">Portfolio Configuration</span>
        </div>
        """, unsafe_allow_html=True)

        # Optimization Model Selection
        model_type = st.selectbox(
            "Optimization Model",
            options=["Black-Litterman", "Markowitz"],
            index=0,
            key="model_type_select",
            help="Black-Litterman starts from the returns implied by market capitalizations and lets you "
                 "add your own views. Markowitz estimates expected returns from price history only."
        )

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Optimization Objective (Only visible for Markowitz)
        obj_function = "Max Sharpe"
        target_volatility = 0.20
        
        if model_type == "Markowitz":
            obj_function = st.selectbox(
                "Optimization Objective",
                options=["Min Variance", "Max Sharpe", "Maximise Return for a Given Risk", "Minimise Risk for a Given Return"],
                index=0,
                key="obj_function_select",
                help="Min Variance: the lowest-risk portfolio. Max Sharpe: the highest expected return "
                     "per unit of risk, with a 3% risk-free rate. Maximise Return for a Given Risk: the "
                     "highest expected return that stays within a target volatility. Minimise Risk for a "
                     "Given Return: the lowest risk that reaches at least a target return."
            )
            
            if obj_function == "Maximise Return for a Given Risk":
                target_volatility = st.number_input(
                    "Target Volatility (Risk)",
                    min_value=0.01,
                    max_value=1.00,
                    value=0.20,
                    step=0.01,
                    format="%.2f",
                    help="The highest annual volatility you accept (e.g. 0.20 = 20%). The optimizer "
                         "maximizes expected return without exceeding it."
                )
            
            target_return = 0.10
            if obj_function == "Minimise Risk for a Given Return":
                target_return = st.number_input(
                    "Target Return",
                    min_value=-0.50,
                    max_value=2.00,
                    value=0.10,
                    step=0.01,
                    format="%.2f",
                    help="The lowest expected annual return you accept (e.g. 0.10 = 10%). The optimizer "
                         "minimizes risk while reaching at least this return."
                )
            
        with st.expander("Advanced Optimization Settings"):
            returns_estimator = "capm"
            if model_type == "Markowitz":
                _estimator_label = st.selectbox(
                    "Expected Returns Estimator",
                    options=["CAPM vs. market (cookbook default)", "Historical mean"],
                    index=0,
                    key="returns_estimator_select",
                    help="CAPM derives expected returns from each asset's beta against "
                         "SPY: the PyPortfolioOpt cookbook default, designed for stocks. "
                         "Historical mean uses each asset's own compounded average return: "
                         "less stable, but it does not measure assets against the stock "
                         "market, which suits commodities, bonds or crypto better."
                )
                returns_estimator = "historical" if _estimator_label.startswith("Historical") else "capm"

            gamma_default = 0.0 if model_type == "Markowitz" else 1.0
            l2_gamma = st.slider(
                "L2 Regularization (Gamma)",
                min_value=0.0,
                max_value=2.0,
                value=gamma_default,
                step=0.1,
                help="Controls weight concentration. At 0 the optimizer allocates freely; "
                     "higher values spread weights more evenly, reducing concentration in a few assets. "
                     "Default: 0.0 for Markowitz, 1.0 for Black-Litterman."
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Ticker input
        tickers_input = st.text_input(
            "Tickers (comma-separated)",
            value="",
            placeholder="e.g. AAPL, MSFT, GOOGL, AMZN",
            key="tickers_input",
            help="2 to 20 Yahoo Finance symbols separated by commas: stocks, ETFs, crypto "
                 "(BTC-USD) or, with Markowitz, forex (EURUSD=X)."
        )

        # Parse tickers
        tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]

        # Detect non-equity tickers (crypto, forex, bonds/commodities by known suffixes)
        _crypto_tickers  = [t for t in tickers if t.endswith("-USD") or t.endswith("-BTC")]
        _forex_tickers   = [t for t in tickers if t.endswith("=X")]
        _non_equity      = _crypto_tickers + _forex_tickers
        # Prices in another currency: Yahoo gives listings outside the US an
        # exchange suffix after a dot (SAP.DE, 7203.T, VOD.L; US share classes
        # use a dash, BRK-B), and crypto quoted in euros ends in -EUR.
        _other_currency = [t for t in tickers
                           if re.fullmatch(r"[A-Z0-9\-]+\.[A-Z]{1,3}", t)
                           or (re.fullmatch(r"[A-Z0-9]+-[A-Z]{3}", t) and not t.endswith("-USD"))]

        # Validation
        if len(tickers) == 0:
            st.info("Enter 2 to 20 tickers to begin")
        elif len(tickers) < 2:
            st.warning("Please enter at least 2 tickers")
        elif len(tickers) > 20:
            st.warning("Maximum 20 tickers allowed")
        else:
            st.success(f"{len(tickers)} tickers selected: {', '.join(tickers)}")

        # Black-Litterman is mathematically undefined for forex (no market
        # capitalization exists to build the equilibrium prior) — block it.
        _bl_forex_blocked = bool(_forex_tickers) and model_type == "Black-Litterman"
        if _bl_forex_blocked:
            st.error(
                f"**Black-Litterman cannot be used with forex pairs** "
                f"({', '.join(_forex_tickers)}): the model builds its market-equilibrium "
                f"prior from market capitalizations, and currencies have none. "
                f"Switch to the **Markowitz** model to include forex."
            )
        elif _non_equity:
            _estimator_hint = (
                " Tip: in *Advanced Optimization Settings*, switch the Expected "
                "Returns Estimator to **Historical mean**, which does not measure "
                "assets against the stock market."
                if model_type == "Markowitz" and returns_estimator == "capm" else ""
            )
            # Crypto has weekend prices and stocks do not: the wrapper keeps
            # the days when all of them trade (see run_optimization)
            _calendar_note = (
                " Crypto also trades on weekends: the estimates will use the weekdays "
                "when every asset trades."
                if _crypto_tickers and len(_crypto_tickers) < len(tickers) else ""
            )
            st.warning(
                f"**Model limitation:** {', '.join(_non_equity)} "
                f"{'is' if len(_non_equity) == 1 else 'are'} not equity instruments. "
                "CAPM, the default Markowitz estimator, measures each asset against SPY, a "
                "stock index, and Black-Litterman starts from market capitalizations. Results "
                "for crypto or forex may not be meaningful."
                + _calendar_note + _estimator_hint
            )

        if _other_currency:
            st.warning(
                f"**Currency:** {', '.join(_other_currency)} "
                f"{'is' if len(_other_currency) == 1 else 'are'} priced in a currency other than "
                "the US dollar. PortfolioLab treats every price as dollars: share counts for "
                f"{'it' if len(_other_currency) == 1 else 'them'} will be wrong, because the budget "
                "is in USD"
                + (", and Black-Litterman will compare market capitalizations across currencies"
                   if model_type == "Black-Litterman" else "")
                + ". Returns are measured in each asset's own currency."
            )

        # Portfolio value
        portfolio_value = st.number_input(
            "Portfolio Value ($)",
            min_value=100,
            max_value=10000000,
            value=10000,
            step=1000,
            key="portfolio_value",
            help="Total value of your portfolio in USD"
        )

        # Date range
        use_date_range = st.checkbox("Use custom date range", key="use_date_range_checkbox")

        date_range = None
        if use_date_range:
            col_a, col_b = st.columns(2)
            with col_a:
                start_date = st.date_input(
                    "Start Date",
                    value=datetime.now() - timedelta(days=365*3),
                    min_value=datetime(1950, 1, 1),
                    max_value=datetime.now()
                )
            with col_b:
                end_date = st.date_input(
                    "End Date",
                    value=datetime.now(),
                    max_value=datetime.now()
                )

            if start_date >= end_date:
                st.error("Start date must be before end date")
            else:
                date_range = (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                st.info(f"Using data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    with col2:
        st.markdown("""
        <div class="step-header">
            <div class="step-circle green">2</div>
            <span class="step-title">Investment Views (Optional)</span>
        </div>
        """, unsafe_allow_html=True)

        if model_type == "Markowitz":
            # Must match core/opt_engine.calculate_markowitz_inputs: CAPM (or
            # historical mean) returns and Ledoit-Wolf covariance.
            st.info(
                "**Markowitz** estimates expected returns from price history (CAPM "
                "against SPY by default, or the historical mean in *Advanced "
                "Optimization Settings*) and uses a Ledoit-Wolf shrunk covariance "
                "matrix. It does not take subjective investment views.",
                icon="ℹ️",
            )
            add_views = False
            views = {}
        else:
            # "Market equilibrium" is the Black-Litterman prior, so this
            # explanation only applies to that model.
            st.markdown("""
            <div class="bl-info">
                <strong>What are views?</strong><br>
                Express your expectations for specific assets. Leave empty to use pure market equilibrium.
            </div>
            """, unsafe_allow_html=True)
            add_views = st.checkbox("Add custom investment views", key="add_views_checkbox")

        views = {}
        if add_views and tickers:
            st.markdown("**Enter your expected annual returns and a range around each one:**")

            # Allow user to select which tickers to add views for
            st.caption("Click on the box below and select one or more assets to add your expected returns.")
            selected_for_views = st.multiselect(
                "Select assets to add views for:",
                tickers,
                key="selected_views_ms",
                help="Choose which assets you want to express views on.",
                placeholder="Choose assets to add views..."
            )

            if selected_for_views:
                for ticker in selected_for_views:
                    with st.expander(f"{ticker}", expanded=True):
                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            expected = st.number_input(
                                "Expected Return",
                                min_value=-1.0,
                                max_value=2.0,
                                value=0.15,
                                step=0.01,
                                format="%.2f",
                                key=f"exp_{ticker}",
                                help="Your expected annual return (e.g., 0.15 = 15%)"
                            )

                        with col_b:
                            lower = st.number_input(
                                "Lower Bound",
                                min_value=-1.0,
                                max_value=2.0,
                                value=expected - 0.05,
                                step=0.01,
                                format="%.2f",
                                key=f"low_{ticker}",
                                help="Low end of a range you consider likely, about one standard "
                                     "deviation below your view. Only the width of the range counts: "
                                     "narrower means more confidence."
                            )

                        with col_c:
                            upper = st.number_input(
                                "Upper Bound",
                                min_value=-1.0,
                                max_value=2.0,
                                value=expected + 0.05,
                                step=0.01,
                                format="%.2f",
                                key=f"upp_{ticker}",
                                help="High end of that range, about one standard deviation above "
                                     "your view."
                            )

                        # Validate bounds
                        if lower >= upper:
                            st.error(f"Lower bound must be less than upper bound for {ticker}")
                        elif expected < lower or expected > upper:
                            st.error(f"Expected return must be between bounds for {ticker}")
                        else:
                            views[ticker] = {
                                'expected': expected,
                                'lower': lower,
                                'upper': upper
                            }
                            st.success(f"View added: {expected*100:.1f}% ({lower*100:.1f}% to {upper*100:.1f}%)")
            else:
                st.info("Select assets from the list above to add your investment views")

        if not add_views and model_type == "Black-Litterman":
            st.info("Using pure market equilibrium (no custom views)")

    # ── Run Optimization ──
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.5, 1, 1.5])

    with col2:
        optimize_button = st.button(
            "Run Optimization",
            type="primary",
            width='stretch',
            disabled=(len(tickers) < 2 or len(tickers) > 20 or _bl_forex_blocked)
        )

    # Run optimization
    if optimize_button:
        # P2: Intelligent Progress Bar
        progress_bar = st.progress(5, text="🚀 Initializing optimization engine...")

        def update_progress(message):
            import time
            msg_lower = message.lower()
            
            if "downloading" in msg_lower:
                progress_bar.progress(25, text=f"📥 {message}")
            elif "calculating market" in msg_lower or "markowitz inputs" in msg_lower:
                progress_bar.progress(50, text=f"🧮 {message}")
            elif "optimizing portfolio" in msg_lower or "incorporating" in msg_lower:
                progress_bar.progress(75, text=f"⚙️ {message}")
            elif "calculating share" in msg_lower or "efficient frontier" in msg_lower:
                progress_bar.progress(90, text=f"📊 {message}")
            elif "complete" in msg_lower:
                progress_bar.progress(100, text=f"✅ {message}")
                time.sleep(0.5)
            else:
                pass # minor updates can be ignored by the main bar

        # Save configuration
        save_config(tickers, portfolio_value, date_range, views if add_views else None)

        # Run optimization
        result = run_optimization(
            tickers=tickers,
            portfolio_value=portfolio_value,
            date_range=date_range,
            views=views if (add_views and views) else None,
            progress_callback=update_progress,
            model_type=model_type,
            obj_function=obj_function,
            target_volatility=target_volatility,
            target_return=target_return if model_type == "Markowitz" else 0.15,
            l2_gamma=l2_gamma,
            returns_estimator=returns_estimator
        )

        # Clear progress
        progress_bar.empty()

        # Save result
        if result['success']:
            save_result(result)
            st.success("Optimization completed successfully!")
        else:
            error_msg = result.get('error', 'Unknown error')
            if "Could not fetch market size" in error_msg:
                # Black-Litterman only (core/opt_engine.download_market_caps): its
                # prior needs every asset's market cap. Yahoo rate-limits that
                # request from shared cloud servers (seen in production on
                # 2026-09-26), and some symbols have none. The inputs are fine
                # either way, and Markowitz does not need market caps.
                if "neither totalAssets nor marketCap" in error_msg:
                    st.error(
                        "⚠️ **No market capitalization available**: Black-Litterman builds its "
                        "prior from market capitalizations, and Yahoo Finance has none for one of "
                        "these assets. Remove it, or switch to **Markowitz**, which does not use "
                        f"them.\n\nDetails: {error_msg}"
                    )
                else:
                    st.error(
                        "⚠️ **Market data temporarily unavailable**: Yahoo Finance is limiting "
                        "requests right now, so Black-Litterman could not fetch the market "
                        "capitalizations its prior needs. Try again in a minute, or switch to "
                        f"**Markowitz**, which does not use them.\n\nDetails: {error_msg}"
                    )
            elif ("No data found" in error_msg or "No price data found" in error_msg
                  or "Download failed" in error_msg):
                st.error(f"⚠️ **Data Error**: Could not download data for one or more tickers. Please verify the tickers are valid on Yahoo Finance.\n\nDetails: {error_msg}")
            elif "in common" in error_msg:
                # utils/optimizer_wrapper: too few dates with a price for every asset
                st.error(f"⚠️ **Not enough data in common**: {error_msg.split(': ', 1)[-1]}")
            elif "Not enough data" in error_msg or "insufficient" in error_msg.lower():
                # core/opt_engine.download_data: the whole download has fewer
                # than MIN_DATA_POINTS rows, i.e. the date range is too short.
                st.error(f"⚠️ **Not enough data**: the selected date range contains fewer than 20 trading days. Choose a longer range.\n\nDetails: {error_msg}")
            elif "exceeding the risk-free rate" in error_msg:
                # PyPortfolioOpt's max_sharpe needs one asset above the risk-free rate
                _next_step = (
                    "Try the Min Variance objective, or another date range."
                    if model_type == "Markowitz" else
                    "Add a view above 3% for an asset you expect to do better, try another date range, or use Markowitz."
                )
                st.error(f"⚠️ **No asset beats the risk-free rate**: maximizing the Sharpe ratio needs at least one asset whose expected return is above the 3% risk-free rate, and none is here. {_next_step}\n\nDetails: {error_msg}")
            elif "optimization" in error_msg.lower() or "solver" in error_msg.lower() or "Infeasible" in error_msg:
                st.error(f"⚠️ **Optimization Failed**: no portfolio meets the request. With a target, it may be out of reach for these assets (a volatility below their minimum, or a return above their highest); the details say which.\n\nDetails: {error_msg}")
            else:
                st.error(f"⚠️ **Optimization failed**: {error_msg.rstrip('.')}. Please check your inputs and try again.")

    # ── Display Results ──
    result = get_result()

    if result and result.get('success'):
        st.markdown("<br>", unsafe_allow_html=True)

        # Results header
        st.markdown("""
        <div class="step-header">
            <div class="step-circle amber">3</div>
            <span class="step-title">Optimization Results</span>
        </div>
        """, unsafe_allow_html=True)

        # Metrics cards
        metrics = result.get('metrics', {})
        num_assets = len([w for w in result.get('weights', {}).values() if w > MIN_WEIGHT_THRESHOLD])

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                label="Expected Return",
                value=f"{metrics.get('return', 0)*100:.2f}%"
            )

        with col2:
            st.metric(
                label="Volatility",
                value=f"{metrics.get('volatility', 0)*100:.2f}%"
            )

        with col3:
            st.metric(
                label="Sharpe Ratio",
                value=f"{metrics.get('sharpe', 0):.3f}"
            )

        with col4:
            st.metric(
                label="Portfolio Value",
                value=f"${result.get('portfolio_value', 0):,.0f}"
            )

        with col5:
            st.metric(
                label="Assets",
                value=f"{num_assets}"
            )

        # What the three figures are (a caption, not help icons: icons
        # truncate the metric labels on ~1024 px screens)
        st.caption(
            "Expected return, volatility and Sharpe ratio are the model's annual estimates "
            "for this portfolio (ex-ante, 3% risk-free rate), not forecasts. The Historical "
            "Performance tab shows the realized ones. Assets: weights above 0.1%."
        )

        # Overlap check: near-perfectly correlated pairs (two funds tracking
        # the same index, two share classes) look like diversification to the
        # optimizer but aren't. Uses the EMPIRICAL correlation from
        # prices — the stored Ledoit-Wolf covariance deliberately shrinks
        # correlations (VOO-IVV: 0.9997 empirical vs ~0.949 shrunk) and
        # would mask true overlaps.
        _overlap_pairs = []
        try:
            if result.get('prices_clean'):
                _pc = pd.DataFrame.from_dict(result['prices_clean'], orient='index')
                _pc = _pc[[t for t in result.get('tickers', []) if t in _pc.columns]]
                if _pc.shape[1] >= 2:
                    _emp_corr = _pc.pct_change().corr()
                    _overlap_pairs = find_highly_correlated_pairs(
                        _emp_corr.values, list(_emp_corr.columns)
                    )
        except Exception:
            pass  # a failed overlap check must never break the results page
        if _overlap_pairs:
            _pairs_txt = "; ".join(
                f"**{a}** ↔ **{b}** ({c:.2f})" for a, b, c in _overlap_pairs[:5]
            )
            st.info(
                f"🔗 **Possible overlapping holdings** — these assets are almost "
                f"perfectly correlated (≥ 0.95): {_pairs_txt}. The optimizer "
                f"treats them as separate assets, but the diversification "
                f"between them is largely illusory (for example two funds that "
                f"track the same index, such as VOO and IVV, or two share "
                f"classes such as GOOGL and GOOG)."
            )

        # Data notes (utils/optimizer_wrapper._data_notes): when the
        # estimation window is shorter than the download, say why.
        _notes = result.get('data_notes') or {}
        _window = result.get('full_data_range')
        _window_txt = f": {_window[0]} to {_window[1]}" if _window else ""
        if _notes.get('late_assets'):
            _late_txt = ", ".join(f"**{t}** from {d}" for t, d in _notes['late_assets'])
            st.info(
                f"📅 **Shorter common history**: prices start on {_notes['data_start']}, but "
                f"{_late_txt}. The estimates use only the dates when every asset has a "
                f"price{_window_txt}."
            )
        if _notes.get('mixed_calendar'):
            st.info(
                "📅 **Weekend prices**: some of these assets trade on weekends (crypto) and others do "
                "not. The estimates use the days when all of them trade, so weekend moves count "
                "toward the following Monday."
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Tabs for different visualizations
        # We only show the "Returns Analysis" tab if the model wasn't Markowitz
        tabs_list = ["Allocation", "Returns Analysis", "Historical Performance", "Correlation", "Detailed Breakdown"]
        
        model_type = result.get('model_type', 'Black-Litterman')
        is_markowitz = model_type == "Markowitz"
        
        if is_markowitz:
            tabs_list.remove("Returns Analysis")
            tabs_list.insert(1, "Efficient Frontier")
            
        tabs = st.tabs(tabs_list)

        # To keep code clean we index dynamically or map
        tab_mapping = {name: tab for name, tab in zip(tabs_list, tabs)}

        with tab_mapping["Allocation"]:
            st.markdown("### Portfolio Allocation")

            col1, col2 = st.columns([1, 1])

            with col1:
                # Pie chart
                weights = result.get('weights', {})
                fig_pie = create_allocation_pie(weights)
                st.plotly_chart(fig_pie, width='stretch', config={'scrollZoom': False})

            with col2:
                st.markdown("#### Optimal Weights")

                # Weights and whole shares, with the same columns as the PDF.
                # Target Value = weight x budget, before rounding to whole
                # shares; Actual Value = shares x the price they were bought at.
                allocation = result.get('allocation', {})
                latest_prices = result.get('latest_prices') or {}
                weights_data = []
                for ticker, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
                    if weight > MIN_WEIGHT_THRESHOLD:
                        shares = allocation.get(ticker, 0)
                        price = latest_prices.get(ticker)
                        weights_data.append({
                            'Asset': ticker,
                            'Weight': f"{weight*100:.2f}%",
                            'Shares': shares,
                            'Price': f"${price:,.2f}" if price else "N/A",
                            'Target Value': f"${weight * result['portfolio_value']:,.2f}",
                            'Actual Value': f"${shares * price:,.2f}" if price else "N/A",
                        })

                if weights_data:
                    df_weights = pd.DataFrame(weights_data)
                    st.dataframe(df_weights, width='stretch', hide_index=True)

                _prices_as_of = (result.get('full_data_range') or (None, None))[1]
                st.caption(
                    f"Shares are bought at each asset's close on {_prices_as_of}, the last day with a price for every asset. "
                    f"Cash left over: ${result.get('leftover', 0):,.2f}."
                    + ("" if is_markowitz else
                       " Black-Litterman's market weights use today's market capitalizations.")
                )

                if result.get('allocation_method') == 'greedy':
                    st.caption(
                        "ℹ️ Share counts were computed with the greedy method "
                        "(the exact integer-optimization solver was unavailable or "
                        "found no solution for this run). Weights are unaffected; "
                        "whole-share rounding may differ slightly from the exact optimum."
                    )

        if "Efficient Frontier" in tab_mapping:
            with tab_mapping["Efficient Frontier"]:
                st.markdown("### Efficient Frontier")
                st.caption(
                    "The efficient frontier is the set of portfolios with the highest expected return for "
                    "each level of risk, from the same expected returns and covariance as the optimization. "
                    "It is drawn without L2 regularization, so with a gamma above 0 your portfolio (amber) "
                    "can sit below the curve."
                )
                ef_data = result.get('ef_data')
                if ef_data:
                    # Build selected portfolio marker from the actual optimization result
                    obj_fn = result.get('obj_function', 'Max Sharpe')
                    selected_portfolio = {
                        'ret': metrics.get('return', 0),
                        'risk': metrics.get('volatility', 0),
                        'sharpe': metrics.get('sharpe', 0),
                        'label': 'Portfolio',
                    }
                    fig_ef = create_efficient_frontier_chart(ef_data, selected_portfolio=selected_portfolio)
                    # Use columns to center the fixed-width plot
                    col_left, col_center, col_right = st.columns([1, 6, 1])
                    with col_center:
                        st.plotly_chart(fig_ef, width='content', config={'scrollZoom': False})
                else:
                    st.info("Efficient Frontier data is not available for this run.")

        if "Returns Analysis" in tab_mapping:
            with tab_mapping["Returns Analysis"]:
                st.markdown("### Returns Analysis")
                st.caption(
                    "Prior: the returns implied by market capitalizations (the market equilibrium). "
                    "Posterior: the Black-Litterman blend of the prior and your views, which the "
                    "optimizer uses. Assets without a view have no view bar."
                )

                # Returns comparison chart
                market_prior = result.get('market_prior', {})
                posterior = result.get('posterior', {})
                viewdict = result.get('viewdict', {})

                fig_returns = create_returns_comparison(
                    market_prior=market_prior,
                    posterior=posterior,
                    views=viewdict if viewdict else None
                )
                st.plotly_chart(fig_returns, width='stretch', config={'scrollZoom': False})

                # Show numerical comparison
                st.markdown("#### Numerical Comparison")

                views_detail = result.get('views_detail', {})
                comparison_data = []
                for ticker in market_prior.keys():
                    row = {
                        'Asset': ticker,
                        'Prior': f"{market_prior[ticker]*100:.2f}%",
                    }
                    if viewdict:
                        row['View'] = f"{viewdict.get(ticker, 0)*100:.2f}%" if ticker in viewdict else "N/A"
                        detail = views_detail.get(ticker, {}) if views_detail else {}
                        if detail:
                            row['Lower'] = f"{detail.get('lower', 0)*100:.2f}%"
                            row['Upper'] = f"{detail.get('upper', 0)*100:.2f}%"
                        else:
                            row['Lower'] = "N/A"
                            row['Upper'] = "N/A"
                    row['Posterior'] = f"{posterior[ticker]*100:.2f}%"
                    comparison_data.append(row)

                df_comparison = pd.DataFrame(comparison_data)
                st.dataframe(df_comparison, width='stretch', hide_index=True)

        with tab_mapping["Historical Performance"]:
            st.markdown("### Historical Performance vs S&P 500")

            # Get date range from result or use default
            date_range = result.get('date_range', None)
            start_date = date_range[0] if date_range else None

            # Create historical performance chart
            try:
                weights = result.get('weights', {})
                tickers = result.get('tickers', [])
                portfolio_value = result.get('portfolio_value', 10000)

                # Reuse pre-downloaded prices from optimization result
                prices_clean_dict = result.get('prices_clean', None)
                prices_df = None
                if prices_clean_dict:
                    try:
                        prices_df = pd.DataFrame.from_dict(prices_clean_dict, orient='index')
                        prices_df.index = pd.to_datetime(prices_df.index)
                        prices_df = prices_df.sort_index()
                    except Exception:
                        prices_df = None

                # Period selector (horizontal radio buttons)
                period_options = ["1M", "6M", "YTD", "1Y", "5Y", "All"]
                selected_period = st.radio(
                    "Time period",
                    period_options,
                    index=period_options.index("All"),
                    horizontal=True,
                    key="backtest_period",
                    label_visibility="collapsed",
                )

                fig_historical, bt_result = create_historical_performance_chart(
                    weights=weights,
                    tickers=tickers,
                    portfolio_value=portfolio_value,
                    benchmark='SPY',
                    initial_date=start_date,
                    prices_data=prices_df,
                    period=selected_period,
                    model_type=model_type,
                )

                st.plotly_chart(fig_historical, width='stretch', config={'scrollZoom': False})

                # Backtest metrics: the same rows and numbers as the PDF's
                # Historical Performance page (core.backtest.prepare_backtest_prices)
                if bt_result is not None:
                    _bt_start, _bt_end = bt_result.dates[0], bt_result.dates[-1]
                    st.markdown("#### Backtest metrics")
                    st.caption(
                        f"Realized over the full backtest period, {_bt_start} to {_bt_end}, "
                        "whichever window the chart shows."
                    )
                    col_bl, col_spy = st.columns(2)

                    portfolio_name = f"{model_type} Portfolio"
                    
                    with col_bl:
                        st.markdown(f"**{portfolio_name}**")
                        pm = bt_result.portfolio_metrics
                        st.metric("Annualized Return", f"{pm.annualized_return:.2f}%")
                        st.metric("Annualized Volatility", f"{pm.annualized_volatility:.2f}%")
                        st.metric("Max Drawdown", f"{pm.max_drawdown:.2f}%")
                        st.metric("Sharpe Ratio", f"{pm.sharpe_ratio:.2f}")
                        st.metric("Sortino Ratio", f"{pm.sortino_ratio:.2f}")
                        st.metric("Calmar Ratio", f"{pm.calmar_ratio:.2f}")
                    with col_spy:
                        st.markdown("**SPY Benchmark**")
                        bm = bt_result.benchmark_metrics
                        st.metric("Annualized Return", f"{bm.annualized_return:.2f}%")
                        st.metric("Annualized Volatility", f"{bm.annualized_volatility:.2f}%")
                        st.metric("Max Drawdown", f"{bm.max_drawdown:.2f}%")
                        st.metric("Sharpe Ratio", f"{bm.sharpe_ratio:.2f}")
                        st.metric("Sortino Ratio", f"{bm.sortino_ratio:.2f}")
                        st.metric("Calmar Ratio", f"{bm.calmar_ratio:.2f}")

                # What this backtest is, and is not
                st.caption(
                    "In-sample backtest: the weights were estimated from this same price history, so it "
                    "does not show how they would have done out of sample, and it tends to flatter the "
                    "optimized portfolio. It keeps the target weights every day (daily rebalancing) and "
                    "ignores whole-share rounding, costs and taxes. The chart rebases returns to 0% at "
                    "the start of the selected window. Past performance does not guarantee future results."
                )

            except Exception as e:
                st.error(f"Could not generate historical performance chart: {e}")

        with tab_mapping["Correlation"]:
            st.markdown("### Correlation Matrix")
            st.caption(
                "Correlations implied by the Ledoit-Wolf shrunk covariance matrix estimated from daily "
                "returns, the risk model both optimizers start from. Shrinkage pulls every correlation "
                "toward zero, so these are never stronger than the raw price correlations (the overlap "
                "check above uses raw ones). Blue: assets that tend to move together; red: assets "
                "that tend to move in opposite directions."
            )

            # Correlation heatmap
            if 'covariance_matrix' in result and result['covariance_matrix']:
                try:
                    cov_matrix = np.array(result['covariance_matrix'])
                    # Labels in the matrix's own order (see optimizer_wrapper)
                    fig_corr = create_correlation_heatmap(
                        cov_matrix, result.get('covariance_tickers') or result['tickers'])
                    st.plotly_chart(fig_corr, width='stretch', config={'scrollZoom': False})
                except Exception as e:
                    st.warning(f"Could not display correlation matrix: {e}")
            else:
                st.info("The correlation matrix shows the relationships between assets. It will be available after running an optimization.")

        with tab_mapping["Detailed Breakdown"]:
            st.markdown("### Detailed Breakdown")

            st.markdown("#### Portfolio Summary")
            st.markdown(f"**Total Value:** ${result['portfolio_value']:,.2f}")
            st.markdown(f"**Number of Assets:** {num_assets}")
            st.markdown(f"**Cash Remaining:** ${result.get('leftover', 0):,.2f}")

            # The periods each part of the result used (see optimizer_wrapper)
            full_range = result.get('full_data_range') or result.get('date_range')
            if full_range:
                st.markdown(f"**Price Data:** {full_range[0]} to {full_range[1]} "
                            "(dates with a price for every asset: expected returns, covariance "
                            "and share prices)")
            if result.get('backtest_range'):
                bt_start, bt_end = result['backtest_range']
                st.markdown(f"**Backtest Period:** {bt_start} to {bt_end} "
                            "(days with a price for every asset and SPY)")

            st.markdown("#### Model Settings")
            _objective = result.get('obj_function', 'Max Sharpe')
            if _objective == "Maximise Return for a Given Risk" and result.get('target_volatility') is not None:
                _objective += f" (target volatility {result['target_volatility']*100:.0f}%)"
            elif _objective == "Minimise Risk for a Given Return" and result.get('target_return') is not None:
                _objective += f" (target return {result['target_return']*100:.0f}%)"
            st.markdown(f"**Model:** {model_type}")
            st.markdown(f"**Objective:** {_objective}")
            if is_markowitz:
                _estimator = ("Historical mean" if result.get('returns_estimator') == "historical"
                              else "CAPM against SPY")
                st.markdown(f"**Expected Returns:** {_estimator}")
            else:
                st.markdown(f"**Expected Returns:** market-implied prior"
                            + (" blended with your views" if result.get('viewdict') else ""))
            st.markdown("**Covariance:** Ledoit-Wolf shrinkage")
            if result.get('l2_gamma') is not None:
                st.markdown(f"**L2 Regularization (Gamma):** {result['l2_gamma']:.1f}")
            st.markdown(f"**Risk-Free Rate:** {result.get('risk_free_rate', 0.03)*100:.0f}%")
            st.markdown(f"**Optimization Date:** {result.get('timestamp', 'N/A')[:10]}")

        # ── Export Results (outside tabs, always visible) ──
        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("#### Export Results")

        from utils.pdf_generator import generate_portfolio_pdf
        from utils.optimizer_wrapper import run_backtest

        try:
            # Check if logo exists
            logo_path = None
            for possible_logo in ['assets/PortfolioLab.png', 'assets/Finance for all.png', 'assets/logo.png']:
                if os.path.exists(possible_logo):
                    logo_path = possible_logo
                    break

            # Add historical validation data to result if not already present
            if 'historical_data' not in result or result['historical_data'] is None:
                with st.spinner("Generating historical validation data..."):
                    try:
                        analysis_date_range = result.get('date_range', None)
                        historical_data = run_backtest(result, date_range=analysis_date_range)
                        if historical_data:
                            result['historical_data'] = historical_data
                        else:
                            result['historical_data'] = None
                    except Exception:
                        result['historical_data'] = None

            # Generate PDF
            pdf_bytes = generate_portfolio_pdf(result, logo_path=logo_path)

            st.download_button(
                label="Download Portfolio Report (PDF)",
                data=pdf_bytes,
                file_name=f"portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                type="primary"
            )
        except Exception as e:
            logger.error("PDF generation failed: %s", e, exc_info=True)
            st.error("❌ Could not generate the PDF report. Please try again or contact support if the issue persists.")

    elif result and not result.get('success'):
        error_msg = result.get('error', 'Unknown error')
        if "No data found" in error_msg or "Download failed" in error_msg:
            st.error(f"⚠️ **Data Error**: Could not download data for one or more tickers. Please verify the tickers are valid on Yahoo Finance.")
        else:
            st.error(f"⚠️ **Last optimization failed**: {error_msg}")


    # ── Render Footer ──
    from utils.styles import render_footer
    render_footer()

if __name__ == "__main__":
    main()
