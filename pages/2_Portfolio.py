"""
Portfolio Page - Black-Litterman and Markowitz optimization
Layout: no sidebar, top navbar; the form (assets and budget, model and goal),
then the results (figures, notes, tabs, PDF report).
"""

import logging
import os
import re
from datetime import datetime, timedelta

import utils.ssl_fix  # noqa: F401 — applies SSL cert fix on import

import streamlit as st
import pandas as pd
import numpy as np

from utils.session_manager import init_session_state, save_config, save_result, get_result
from utils.optimizer_wrapper import run_optimization, find_highly_correlated_pairs
from core.constants import MIN_WEIGHT_THRESHOLD, OBJECTIVE_LABELS, goal_text
from core.example_market import EXAMPLE_PORTFOLIOS
from utils.visualizations import (
    create_correlation_heatmap,
    create_returns_comparison,
    create_allocation_chart,
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

# What each model does, in the model selector's own words
MODEL_LABELS = {
    "Black-Litterman": "Black-Litterman: market returns plus your views",
    "Markowitz": "Markowitz: returns from price history",
}

ESTIMATOR_OPTIONS = ["CAPM vs. market (cookbook default)", "Historical mean"]


def _apply_example_link():
    """
    Fill the form from a Home page example link (./Portfolio?example=<key>).

    Runs before any widget is created, like any change to a widget's state,
    and only once: the parameter is removed from the URL, so later reruns
    keep whatever the user changes. The user still presses Run.
    """
    key = st.query_params.get("example")
    if key is None:
        return
    del st.query_params["example"]
    example = EXAMPLE_PORTFOLIOS.get(key)
    if example is None:
        return

    st.session_state["tickers_input"] = ", ".join(example["tickers"])
    st.session_state["model_type_select"] = "Markowitz"
    st.session_state["obj_function_select"] = example["objective"]
    if "target_volatility" in example:
        st.session_state["target_volatility_pct"] = example["target_volatility"] * 100
    if "target_return" in example:
        st.session_state["target_return_pct"] = example["target_return"] * 100
    st.session_state["returns_estimator_select"] = (
        ESTIMATOR_OPTIONS[1] if example.get("returns_estimator") == "historical" else ESTIMATOR_OPTIONS[0])
    st.toast(f"{example['title']} example loaded. Press Run optimization to see the result.")


def _step(number: int, title: str) -> None:
    st.markdown(f"""
    <div class="step-header">
        <div class="step-circle">{number}</div>
        <span class="step-title">{title}</span>
    </div>
    """, unsafe_allow_html=True)


def _objective_text(result: dict) -> str:
    """The run's goal: plain name, target and the textbook name (as in the PDF)."""
    objective = result.get('obj_function', 'Max Sharpe')
    goal = goal_text(objective, result.get('target_volatility'), result.get('target_return'))
    return f"{goal} ({objective})"


def main():
    """Main optimizer page."""
    _apply_example_link()

    # ── Page Header ──
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h1 class="page-title">Portfolio</h1>
        <p class="page-subtitle">Choose your assets and a goal: get the optimal weights, the whole shares to buy and how the portfolio would have done.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Form: what to optimize (left) and how (right) ──
    col1, spacer, col2 = st.columns([1, 0.08, 1])

    with col1:
        _step(1, "Assets and budget")

        tickers_input = st.text_input(
            "Tickers",
            value="",
            placeholder="e.g. AAPL, MSFT, GOOGL, AMZN",
            key="tickers_input",
            help="Yahoo Finance symbols: stocks, ETFs, crypto (BTC-USD) or, with Markowitz, "
                 "forex (EURUSD=X)."
        )
        st.caption("2 to 20 symbols, separated by commas.")

        # Parse tickers
        tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]

        # Notes on the tickers go right under them, but depend on the model
        # chosen in the right column: filled in further down.
        ticker_notes = st.container()

        portfolio_value = st.number_input(
            "Budget ($)",
            min_value=100,
            max_value=10000000,
            value=10000,
            step=1000,
            key="portfolio_value",
            help="The amount to invest, in US dollars. The weights become whole shares for it."
        )

        # Date range
        use_date_range = st.checkbox("Use custom date range", key="use_date_range_checkbox",
                                     help="By default the whole history the assets share is used.")

        date_range = None
        if use_date_range:
            col_a, col_b = st.columns(2)
            with col_a:
                start_date = st.date_input(
                    "Start date",
                    value=datetime.now() - timedelta(days=365*3),
                    min_value=datetime(1950, 1, 1),
                    max_value=datetime.now()
                )
            with col_b:
                end_date = st.date_input(
                    "End date",
                    value=datetime.now(),
                    max_value=datetime.now()
                )

            if start_date >= end_date:
                st.error("The start date must be before the end date.")
            else:
                date_range = (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

    with col2:
        _step(2, "Model and goal")

        # Markowitz first (2026-09-27): it needs no market capitalizations,
        # which Yahoo rate-limits on the cloud, so a first run just works
        model_type = st.selectbox(
            "Model",
            options=["Markowitz", "Black-Litterman"],
            index=0,
            format_func=MODEL_LABELS.get,
            key="model_type_select",
            help="Black-Litterman starts from the returns implied by market capitalizations and lets you "
                 "add your own views. Markowitz estimates expected returns from price history only."
        )

        # Black-Litterman always maximizes the Sharpe ratio (cookbook)
        obj_function = "Max Sharpe"
        target_volatility = 0.20
        target_return = 0.10
        add_views = False
        views = {}

        if model_type == "Markowitz":
            obj_function = st.selectbox(
                "Goal",
                options=list(OBJECTIVE_LABELS),
                index=0,
                format_func=OBJECTIVE_LABELS.get,
                key="obj_function_select",
                help="Lowest risk: minimum variance. Best return for the risk: maximum Sharpe ratio, "
                     "with a 3% risk-free rate. Highest return within a risk limit: the most expected "
                     "return with a volatility up to your limit. Lowest risk for a target return: the "
                     "least volatility that reaches at least your return."
            )

            if obj_function == "Maximise Return for a Given Risk":
                target_volatility = st.number_input(
                    "Risk limit (annual volatility, %)",
                    min_value=1.0,
                    max_value=100.0,
                    value=20.0,
                    step=1.0,
                    format="%.1f",
                    key="target_volatility_pct",
                    help="The highest annual volatility you accept, e.g. 20 for 20%."
                ) / 100

            if obj_function == "Minimise Risk for a Given Return":
                target_return = st.number_input(
                    "Target return (annual, %)",
                    min_value=-50.0,
                    max_value=200.0,
                    value=10.0,
                    step=1.0,
                    format="%.1f",
                    key="target_return_pct",
                    help="The lowest expected annual return you accept, e.g. 10 for 10%."
                ) / 100
        else:
            add_views = st.checkbox("Add my own views", key="add_views_checkbox")
            st.caption("Your expected return for some of the assets. Without views, the model uses "
                       "the returns implied by market values.")

            if add_views and tickers:
                selected_for_views = st.multiselect(
                    "Assets with a view",
                    tickers,
                    key="selected_views_ms",
                    placeholder="Choose assets"
                )

                for ticker in selected_for_views:
                    with st.expander(ticker, expanded=True):
                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            expected = st.number_input(
                                "Expected return (%)",
                                min_value=-100.0,
                                max_value=200.0,
                                value=15.0,
                                step=1.0,
                                format="%.1f",
                                key=f"exp_{ticker}",
                                help="Your expected annual return, e.g. 15 for 15%."
                            )

                        with col_b:
                            lower = st.number_input(
                                "Low (%)",
                                min_value=-100.0,
                                max_value=200.0,
                                value=expected - 5.0,
                                step=1.0,
                                format="%.1f",
                                key=f"low_{ticker}",
                                help="Low end of a range you consider likely, about one standard "
                                     "deviation below your view. Only the width of the range counts: "
                                     "narrower means more confidence."
                            )

                        with col_c:
                            upper = st.number_input(
                                "High (%)",
                                min_value=-100.0,
                                max_value=200.0,
                                value=expected + 5.0,
                                step=1.0,
                                format="%.1f",
                                key=f"upp_{ticker}",
                                help="High end of that range, about one standard deviation above "
                                     "your view."
                            )

                        # The inputs are percentages; the engine takes fractions
                        if lower >= upper:
                            st.error(f"For {ticker}, Low must be below High.")
                        elif expected < lower or expected > upper:
                            st.error(f"For {ticker}, the expected return must be between Low and High.")
                        else:
                            views[ticker] = {
                                'expected': expected / 100,
                                'lower': lower / 100,
                                'upper': upper / 100
                            }

        with st.expander("Advanced settings"):
            returns_estimator = "capm"
            if model_type == "Markowitz":
                _estimator_label = st.selectbox(
                    "Expected returns",
                    options=ESTIMATOR_OPTIONS,
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
                "L2 regularization (gamma)",
                min_value=0.0,
                max_value=2.0,
                value=gamma_default,
                step=0.1,
                help="Controls weight concentration. At 0 the optimizer allocates freely; "
                     "higher values spread weights more evenly, reducing concentration in a few assets. "
                     "Default: 0.0 for Markowitz, 1.0 for Black-Litterman."
            )

    # ── Notes on the tickers (left column, under the input) ──
    _crypto_tickers = [t for t in tickers if t.endswith("-USD") or t.endswith("-BTC")]
    _forex_tickers = [t for t in tickers if t.endswith("=X")]
    _non_equity = _crypto_tickers + _forex_tickers
    # Prices in another currency: Yahoo gives listings outside the US an
    # exchange suffix after a dot (SAP.DE, 7203.T, VOD.L; US share classes
    # use a dash, BRK-B), and crypto quoted in euros ends in -EUR.
    _other_currency = [t for t in tickers
                       if re.fullmatch(r"[A-Z0-9\-]+\.[A-Z]{1,3}", t)
                       or (re.fullmatch(r"[A-Z0-9]+-[A-Z]{3}", t) and not t.endswith("-USD"))]

    # Black-Litterman is mathematically undefined for forex (no market
    # capitalization exists to build the equilibrium prior) — block it.
    _bl_forex_blocked = bool(_forex_tickers) and model_type == "Black-Litterman"

    with ticker_notes:
        if len(tickers) == 1:
            st.warning("Enter at least 2 tickers.")
        elif len(tickers) > 20:
            st.warning("Enter 20 tickers at most.")

        if _bl_forex_blocked:
            st.error(
                f"**Black-Litterman cannot be used with forex pairs** "
                f"({', '.join(_forex_tickers)}): the model builds its market-equilibrium "
                f"prior from market capitalizations, and currencies have none. "
                f"Switch to the **Markowitz** model to include forex."
            )
        elif _non_equity:
            _estimator_hint = (
                " Setting *Expected returns* to **Historical mean** under *Advanced "
                "settings* suits them better."
                if model_type == "Markowitz" and returns_estimator == "capm" else ""
            )
            # Crypto has weekend prices and stocks do not: the wrapper keeps
            # the days when all of them trade (see run_optimization)
            _calendar_note = (
                " Crypto also trades on weekends: the estimates use the weekdays "
                "when every asset trades."
                if _crypto_tickers and len(_crypto_tickers) < len(tickers) else ""
            )
            st.warning(
                f"**{', '.join(_non_equity)} {'is' if len(_non_equity) == 1 else 'are'} not "
                f"{'a stock' if len(_non_equity) == 1 else 'stocks'}.** CAPM measures each asset "
                "against SPY, a stock index, and Black-Litterman starts from market values, so "
                "the results may not mean much." + _estimator_hint + _calendar_note
            )

        if _other_currency:
            _one = len(_other_currency) == 1
            st.warning(
                f"**{', '.join(_other_currency)} {'is' if _one else 'are'} priced in another "
                f"currency.** PortfolioLab treats every price as US dollars, so the share "
                f"{'count' if _one else 'counts'} for {'it' if _one else 'them'} will be wrong"
                + (" and Black-Litterman will compare market values across currencies"
                   if model_type == "Black-Litterman" else "")
                + "."
            )

    # ── Run Optimization ──
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.5, 1, 1.5])

    with col2:
        optimize_button = st.button(
            "Run optimization",
            type="primary",
            width='stretch',
            disabled=(len(tickers) < 2 or len(tickers) > 20 or _bl_forex_blocked)
        )

    # Run optimization
    if optimize_button:
        progress_bar = st.progress(5, text="Starting...")

        def update_progress(message):
            msg_lower = message.lower()
            if "downloading" in msg_lower:
                progress_bar.progress(25, text=message)
            elif "calculating market" in msg_lower or "markowitz inputs" in msg_lower:
                progress_bar.progress(50, text=message)
            elif "optimizing portfolio" in msg_lower or "incorporating" in msg_lower:
                progress_bar.progress(75, text=message)
            elif "calculating share" in msg_lower or "efficient frontier" in msg_lower:
                progress_bar.progress(90, text=message)
            elif "complete" in msg_lower:
                progress_bar.progress(100, text=message)

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
                        "**No market capitalization available**: Black-Litterman builds its "
                        "prior from market capitalizations, and Yahoo Finance has none for one of "
                        "these assets. Remove it, or switch to **Markowitz**, which does not use "
                        f"them.\n\nDetails: {error_msg}"
                    )
                else:
                    st.error(
                        "**Market data temporarily unavailable**: Yahoo Finance is limiting "
                        "requests right now, so Black-Litterman could not fetch the market "
                        "capitalizations its prior needs. Try again in a minute, or switch to "
                        f"**Markowitz**, which does not use them.\n\nDetails: {error_msg}"
                    )
            elif ("No data found" in error_msg or "No price data found" in error_msg
                  or "Download failed" in error_msg):
                st.error(f"**No prices found**: Yahoo Finance returned no prices for one or more tickers. Check the symbols; if they are valid, Yahoo may be limiting requests, so try again in a minute.\n\nDetails: {error_msg}")
            elif "in common" in error_msg:
                # utils/optimizer_wrapper: too few dates with a price for every asset
                st.error(f"**Not enough data in common**: {error_msg.split(': ', 1)[-1]}")
            elif "Not enough data" in error_msg or "insufficient" in error_msg.lower():
                # core/opt_engine.download_data: the whole download has fewer
                # than MIN_DATA_POINTS rows, i.e. the date range is too short.
                st.error(f"**Not enough data**: the selected date range contains fewer than 20 trading days. Choose a longer range.\n\nDetails: {error_msg}")
            elif "exceeding the risk-free rate" in error_msg:
                # PyPortfolioOpt's max_sharpe needs one asset above the risk-free rate
                _next_step = (
                    "Try the Lowest risk goal, or another date range."
                    if model_type == "Markowitz" else
                    "Add a view above 3% for an asset you expect to do better, try another date range, or use Markowitz."
                )
                st.error(f"**No asset beats the risk-free rate**: the best return for the risk needs at least one asset whose expected return is above the 3% risk-free rate, and none is here. {_next_step}\n\nDetails: {error_msg}")
            elif "optimization" in error_msg.lower() or "solver" in error_msg.lower() or "Infeasible" in error_msg:
                st.error(f"**No portfolio meets the goal**: with a limit or a target, it may be out of reach for these assets (a risk limit below their lowest risk, or a return above their highest); the details say which.\n\nDetails: {error_msg}")
            else:
                st.error(f"**The optimization failed**: {error_msg.rstrip('.')}. Please check your inputs and try again.")

    # ── Display Results ──
    result = get_result()

    if result and result.get('success'):
        st.markdown("<br>", unsafe_allow_html=True)
        _step(3, "Results")

        metrics = result.get('metrics', {})
        num_assets = len([w for w in result.get('weights', {}).values() if w > MIN_WEIGHT_THRESHOLD])
        model_type = result.get('model_type', 'Black-Litterman')
        is_markowitz = model_type == "Markowitz"

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Expected return", f"{metrics.get('return', 0)*100:.2f}%")
        col2.metric("Volatility", f"{metrics.get('volatility', 0)*100:.2f}%")
        col3.metric("Sharpe ratio", f"{metrics.get('sharpe', 0):.3f}")
        col4.metric("Budget", f"${result.get('portfolio_value', 0):,.0f}")
        col5.metric("Assets", f"{num_assets}")

        # A caption, not help icons: icons truncate the metric labels on
        # ~1024 px screens
        st.caption(
            "The model's annual estimates for these weights (3% risk-free rate), not forecasts. "
            "Historical performance shows what they would have earned."
        )

        # ── Notes about these results: one collapsed box, only when there are any ──
        notes = []

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
            _pairs_txt = "; ".join(f"{a} and {b} ({c:.2f})" for a, b, c in _overlap_pairs[:5])
            notes.append(
                f"**Overlapping holdings**: {_pairs_txt} move almost identically (correlation "
                "of 0.95 or more). The optimizer counts them as separate assets, but holding both "
                "adds little diversification, as with two funds on the same index (VOO and IVV) "
                "or two share classes (GOOGL and GOOG)."
            )

        # Data notes (utils/optimizer_wrapper._data_notes): when the
        # estimation window is shorter than the download, say why.
        _data = result.get('data_notes') or {}
        _window = result.get('full_data_range')
        _window_txt = f": {_window[0]} to {_window[1]}" if _window else ""
        if _data.get('late_assets'):
            _late_txt = ", ".join(f"{t} from {d}" for t, d in _data['late_assets'])
            notes.append(
                f"**Shorter common history**: prices start on {_data['data_start']}, but "
                f"{_late_txt}. The estimates use only the dates when every asset has a "
                f"price{_window_txt}."
            )
        if _data.get('mixed_calendar'):
            notes.append(
                "**Weekend prices**: some of these assets trade on weekends (crypto) and others do "
                "not. The estimates use the days when all of them trade, so weekend moves count "
                "toward the following Monday."
            )

        if notes:
            with st.expander(f"Notes about these results ({len(notes)})", icon=":material/info:"):
                st.markdown("\n".join(f"- {note}" for note in notes))

        st.markdown("<br>", unsafe_allow_html=True)

        # Tabs depend on the model (see CLAUDE.md → Web Tabs)
        second_tab = "Efficient frontier" if is_markowitz else "Returns analysis"
        tabs_list = ["Allocation", second_tab, "Historical performance", "Correlation", "Details"]
        tab_mapping = dict(zip(tabs_list, st.tabs(tabs_list)))

        with tab_mapping["Allocation"]:
            col1, col2 = st.columns([1, 1])

            weights = result.get('weights', {})
            with col1:
                st.plotly_chart(create_allocation_chart(weights), width='stretch',
                                config={'scrollZoom': False})

            with col2:
                # Weights and whole shares, with the same columns as the PDF.
                # Target value = weight x budget, before rounding to whole
                # shares; Actual value = shares x the price they were bought at.
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
                            'Target value': f"${weight * result['portfolio_value']:,.2f}",
                            'Actual value': f"${shares * price:,.2f}" if price else "N/A",
                        })

                if weights_data:
                    st.dataframe(pd.DataFrame(weights_data), width='stretch', hide_index=True)

                _prices_as_of = (result.get('full_data_range') or (None, None))[1]
                st.caption(
                    f"Shares are bought at each asset's close on {_prices_as_of}, the last day with a "
                    f"price for every asset. Cash left over: ${result.get('leftover', 0):,.2f}."
                    + ("" if is_markowitz else
                       " Black-Litterman's market weights use today's market capitalizations.")
                )

                if result.get('allocation_method') == 'greedy':
                    st.caption(
                        "Share counts use the greedy method (the exact solver was not available for "
                        "this run), so they can differ slightly from the exact optimum. The weights "
                        "are the same."
                    )

        if is_markowitz:
            with tab_mapping["Efficient frontier"]:
                st.caption(
                    "Each point on the curve is the highest expected return for its level of risk."
                    + (" It is drawn without L2 regularization, so your portfolio can sit below it."
                       if result.get('l2_gamma') else "")
                )
                ef_data = result.get('ef_data')
                if ef_data:
                    selected_portfolio = {
                        'ret': metrics.get('return', 0),
                        'risk': metrics.get('volatility', 0),
                        'sharpe': metrics.get('sharpe', 0),
                        'label': 'Your portfolio',
                    }
                    fig_ef = create_efficient_frontier_chart(ef_data, selected_portfolio=selected_portfolio)
                    # Use columns to center the fixed-width plot
                    col_left, col_center, col_right = st.columns([1, 6, 1])
                    with col_center:
                        st.plotly_chart(fig_ef, width='content', config={'scrollZoom': False})
                else:
                    st.info("The efficient frontier is not available for this run.")
        else:
            with tab_mapping["Returns analysis"]:
                st.caption(
                    "Prior: the returns implied by market capitalizations. Posterior: the prior "
                    "blended with your views, which the optimizer uses."
                )

                market_prior = result.get('market_prior', {})
                posterior = result.get('posterior', {})
                viewdict = result.get('viewdict', {})

                fig_returns = create_returns_comparison(
                    market_prior=market_prior,
                    posterior=posterior,
                    views=viewdict if viewdict else None
                )
                st.plotly_chart(fig_returns, width='stretch', config={'scrollZoom': False})

                views_detail = result.get('views_detail', {})
                comparison_data = []
                for ticker in market_prior.keys():
                    row = {
                        'Asset': ticker,
                        'Prior': f"{market_prior[ticker]*100:.2f}%",
                    }
                    if viewdict:
                        row['View'] = f"{viewdict.get(ticker, 0)*100:.2f}%" if ticker in viewdict else "—"
                        detail = views_detail.get(ticker, {}) if views_detail else {}
                        row['Low'] = f"{detail.get('lower', 0)*100:.2f}%" if detail else "—"
                        row['High'] = f"{detail.get('upper', 0)*100:.2f}%" if detail else "—"
                    row['Posterior'] = f"{posterior[ticker]*100:.2f}%"
                    comparison_data.append(row)

                st.dataframe(pd.DataFrame(comparison_data), width='stretch', hide_index=True)

        with tab_mapping["Historical performance"]:
            # Get date range from result or use default
            date_range = result.get('date_range', None)
            start_date = date_range[0] if date_range else None

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

                st.caption(
                    "How these weights would have done against SPY (the S&P 500). In-sample: the "
                    "weights come from this same price history, which flatters them. Rebalanced "
                    "daily; no rounding, costs or taxes. Past performance does not guarantee "
                    "future results."
                )

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
                    st.markdown("#### Backtest figures")
                    st.caption(f"Over the full period, {_bt_start} to {_bt_end}, whichever window the chart shows.")
                    pm, bm = bt_result.portfolio_metrics, bt_result.benchmark_metrics
                    rows = [
                        ("Annualized return", f"{pm.annualized_return:.2f}%", f"{bm.annualized_return:.2f}%"),
                        ("Annualized volatility", f"{pm.annualized_volatility:.2f}%", f"{bm.annualized_volatility:.2f}%"),
                        ("Max drawdown", f"{pm.max_drawdown:.2f}%", f"{bm.max_drawdown:.2f}%"),
                        ("Sharpe ratio", f"{pm.sharpe_ratio:.2f}", f"{bm.sharpe_ratio:.2f}"),
                        ("Sortino ratio", f"{pm.sortino_ratio:.2f}", f"{bm.sortino_ratio:.2f}"),
                        ("Calmar ratio", f"{pm.calmar_ratio:.2f}", f"{bm.calmar_ratio:.2f}"),
                    ]
                    st.dataframe(
                        pd.DataFrame(rows, columns=["", "Your portfolio", "SPY"]),
                        width='stretch', hide_index=True,
                    )

            except Exception as e:
                st.error(f"Could not generate historical performance chart: {e}")

        with tab_mapping["Correlation"]:
            st.caption(
                "From the shrunk covariance matrix the optimizer uses (Ledoit-Wolf), which pulls every "
                "correlation toward zero. Blue: assets that tend to move together; red: in opposite "
                "directions."
            )

            if 'covariance_matrix' in result and result['covariance_matrix']:
                try:
                    cov_matrix = np.array(result['covariance_matrix'])
                    # Labels in the matrix's own order (see optimizer_wrapper)
                    fig_corr = create_correlation_heatmap(
                        cov_matrix, result.get('covariance_tickers') or result['tickers'])
                    st.plotly_chart(fig_corr, width='stretch', config={'scrollZoom': False})
                except Exception as e:
                    st.warning(f"Could not display correlation matrix: {e}")

        with tab_mapping["Details"]:
            col_a, col_b = st.columns(2, gap="large")

            with col_a:
                st.markdown("#### Portfolio")
                # Dollar signs escaped: two in one markdown string open a math formula
                lines = [
                    f"**Budget:** \\${result['portfolio_value']:,.2f}",
                    f"**Assets:** {num_assets}",
                    f"**Cash left over:** \\${result.get('leftover', 0):,.2f}",
                ]
                # The periods each part of the result used (see optimizer_wrapper)
                full_range = result.get('full_data_range') or result.get('date_range')
                if full_range:
                    lines.append(f"**Price data:** {full_range[0]} to {full_range[1]} "
                                 "(dates with a price for every asset: expected returns, covariance "
                                 "and share prices)")
                if result.get('backtest_range'):
                    bt_start, bt_end = result['backtest_range']
                    lines.append(f"**Backtest period:** {bt_start} to {bt_end} "
                                 "(days with a price for every asset and SPY)")
                st.markdown("  \n".join(lines))

            with col_b:
                st.markdown("#### Model settings")
                lines = [
                    f"**Model:** {model_type}",
                    f"**Goal:** {_objective_text(result)}",
                ]
                if is_markowitz:
                    _estimator = ("Historical mean" if result.get('returns_estimator') == "historical"
                                  else "CAPM against SPY")
                    lines.append(f"**Expected returns:** {_estimator}")
                else:
                    lines.append("**Expected returns:** market-implied prior"
                                 + (" blended with your views" if result.get('viewdict') else ""))
                lines.append("**Covariance:** Ledoit-Wolf shrinkage")
                if result.get('l2_gamma') is not None:
                    lines.append(f"**L2 regularization (gamma):** {result['l2_gamma']:.1f}")
                lines.append(f"**Risk-free rate:** {result.get('risk_free_rate', 0.03)*100:.0f}%")
                lines.append(f"**Run on:** {result.get('timestamp', 'N/A')[:10]}")
                st.markdown("  \n".join(lines))

        # ── Report (outside tabs, always visible) ──
        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("#### Report")

        from utils.pdf_generator import build_report_pdf

        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "PortfolioLab.png")
        if not os.path.exists(logo_path):
            logo_path = None

        def _report() -> bytes:
            # Deferred: Streamlit calls this only when the button is clicked
            # (on its own thread), so reruns of this page never build the PDF
            try:
                return build_report_pdf(result, logo_path=logo_path)
            except Exception as e:
                logger.error("PDF generation failed: %s", e, exc_info=True)
                raise

        st.download_button(
            label="Download PDF report",
            data=_report,
            file_name=f"portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            type="primary",
            on_click="ignore",
        )
        st.caption("The report is built when you click, which takes a few seconds.")

    # ── Render Footer ──
    from utils.styles import render_footer
    render_footer()


if __name__ == "__main__":
    main()
