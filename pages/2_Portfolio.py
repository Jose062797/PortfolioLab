"""
Portfolio Page - Black-Litterman Streamlit App
Modern layout: no sidebar, top navbar, clean card-based UI
"""

import os
import io
from datetime import datetime, timedelta

import utils.ssl_fix  # noqa: F401 — applies SSL cert fix on import

import streamlit as st
import pandas as pd
import numpy as np

from utils.session_manager import init_session_state, save_config, save_result, get_result, get_history
from utils.optimizer_wrapper import run_optimization
from core.constants import MIN_WEIGHT_THRESHOLD
from utils.visualizations import (
    create_correlation_heatmap,
    create_returns_comparison,
    create_allocation_pie,
    create_allocation_table,
    create_efficient_frontier_chart,
    create_historical_performance_chart
)

# Page configuration
st.set_page_config(
    page_title="Portfolio – PortfolioLab",
    page_icon="BL",
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


def main():
    """Main optimizer page - modern, clean layout."""


    # ── Page Header ──
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h1 class="page-title">Portfolio</h1>
        <p class="page-subtitle">Build your optimal portfolio using advanced optimization models</p>
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
            help="Select the optimization engine. Black-Litterman allows custom views, Markowitz relies only on historical data."
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
                help="Objective function to minimize/maximize. Min Variance seeks the lowest possible risk. Max Sharpe seeks the best risk-adjusted return (using L2 gamma for diversification). Maximise Return for a Given Risk lets you specify a volatility ceiling. Minimise Risk for a Given Return minimizes risk given a return goal."
            )
            
            if obj_function == "Maximise Return for a Given Risk":
                target_volatility = st.number_input(
                    "Target Volatility (Risk)",
                    min_value=0.01,
                    max_value=1.00,
                    value=0.20,
                    step=0.01,
                    format="%.2f",
                    help="The desired portfolio volatility (e.g. 0.20 = 20% annual risk)."
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
                    help="The desired portfolio return (e.g. 0.15 = 15% annual return)."
                )
            
        with st.expander("Advanced Optimization Settings"):
            gamma_default = 0.0 if model_type == "Markowitz" else 1.0
            l2_gamma = st.slider(
                "L2 Regularization (Gamma)",
                min_value=0.0,
                max_value=2.0,
                value=gamma_default,
                step=0.1,
                help="Diversification penalty. "
                     "Markowitz default: 0.0 (pure textbook). "
                     "Black-Litterman default: 1.0 (matches PyPortfolioOpt cookbook). "
                     "Increase to reduce concentration in few assets."
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Ticker input
        tickers_input = st.text_input(
            "Stock Tickers (comma-separated)",
            value="",
            placeholder="e.g. AAPL, MSFT, GOOGL, AMZN",
            key="tickers_input",
            help="Enter 2-20 stock tickers separated by commas (e.g., AAPL, MSFT, GOOGL)"
        )

        # Parse tickers
        tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]

        # Validation
        if len(tickers) == 0:
            st.info("Enter 2 to 20 stock tickers to begin")
        elif len(tickers) < 2:
            st.warning("Please enter at least 2 tickers")
        elif len(tickers) > 20:
            st.warning("Maximum 20 tickers allowed")
        else:
            st.success(f"{len(tickers)} tickers selected: {', '.join(tickers)}")

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

        st.markdown("""
        <div class="bl-info">
            <strong>What are views?</strong><br>
            Express your expectations for specific assets. Leave empty to use pure market equilibrium.
        </div>
        """, unsafe_allow_html=True)

        if model_type == "Markowitz":
            st.info("Markowitz optimization (Standard MVO) uses historical means and covariance matrix directly. It does not support subjective investment views.", icon="ℹ️")
            add_views = False
            views = {}
        else:
            add_views = st.checkbox("Add custom investment views", key="add_views_checkbox")

        views = {}
        if add_views and tickers:
            st.markdown("**Enter your expected annual returns and confidence intervals:**")

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
                                help="Conservative estimate"
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
                                help="Optimistic estimate"
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
            disabled=(len(tickers) < 2 or len(tickers) > 20)
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
            l2_gamma=l2_gamma
        )

        # Clear progress
        progress_bar.empty()

        # Save result
        if result['success']:
            save_result(result)
            st.success("Optimization completed successfully!")
        else:
            error_msg = result.get('error', 'Unknown error')
            if "No data found" in error_msg or "Download failed" in error_msg:
                st.error(f"⚠️ **Data Error**: Could not download data for one or more tickers. Please verify the tickers are valid on Yahoo Finance.\n\nDetails: {error_msg}")
            elif "Not enough data" in error_msg or "insufficient" in error_msg.lower():
                st.error(f"⚠️ **Insufficient Data**: Some assets don't have enough historical data for the selected date range. Try shortening the date range or removing recently listed assets.\n\nDetails: {error_msg}")
            elif "optimization" in error_msg.lower() or "solver" in error_msg.lower() or "Infeasible" in error_msg:
                st.error(f"⚠️ **Optimization Failed**: The mathematical solver could not find a solution. Try adjusting your constraints, target returns, or investment views.\n\nDetails: {error_msg}")
            else:
                st.error(f"⚠️ **Optimization failed**: {error_msg}. Please check your inputs and try again.")

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

                # Show unified weights + shares table
                allocation = result.get('allocation', {})
                weights_data = []
                for ticker, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
                    if weight > MIN_WEIGHT_THRESHOLD:
                        weights_data.append({
                            'Asset': ticker,
                            'Weight': f"{weight*100:.2f}%",
                            'Shares': allocation.get(ticker, 0),
                            'Value': f"${weight * result['portfolio_value']:,.2f}"
                        })

                if weights_data:
                    df_weights = pd.DataFrame(weights_data)
                    st.dataframe(df_weights, width='stretch', hide_index=True)

        if "Efficient Frontier" in tab_mapping:
            with tab_mapping["Efficient Frontier"]:
                st.markdown("### Efficient Frontier")
                st.caption("The Efficient Frontier represents the set of optimal portfolios that offer the highest expected return for a defined level of risk.")
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

                # Backtest metrics (matching PDF Historical Performance section)
                if bt_result is not None:
                    col_bl, col_spy = st.columns(2)
                    
                    portfolio_name = "Markowitz Portfolio" if is_markowitz else "BL Portfolio"
                    
                    with col_bl:
                        st.markdown(f"**{portfolio_name}**")
                        pm = bt_result.portfolio_metrics
                        st.metric("Annualized Return", f"{pm.annualized_return:.2f}%")
                        st.metric("Annualized Volatility", f"{pm.annualized_volatility:.2f}%")
                        st.metric("Sharpe Ratio", f"{pm.sharpe_ratio:.2f}")
                        st.metric("Max Drawdown", f"{pm.max_drawdown:.2f}%")
                        st.metric("Sortino Ratio", f"{pm.sortino_ratio:.2f}")
                        st.metric("Calmar Ratio", f"{pm.calmar_ratio:.2f}")
                    with col_spy:
                        st.markdown("**SPY Benchmark**")
                        bm = bt_result.benchmark_metrics
                        st.metric("Annualized Return", f"{bm.annualized_return:.2f}%")
                        st.metric("Annualized Volatility", f"{bm.annualized_volatility:.2f}%")
                        st.metric("Sharpe Ratio", f"{bm.sharpe_ratio:.2f}")
                        st.metric("Max Drawdown", f"{bm.max_drawdown:.2f}%")
                        st.metric("Sortino Ratio", f"{bm.sortino_ratio:.2f}")
                        st.metric("Calmar Ratio", f"{bm.calmar_ratio:.2f}")

                # Add explanation
                st.caption(
                    "This backtest shows how your optimized portfolio would have performed historically "
                    "compared to the S&P 500 (SPY). Returns are rebased to 0% at the start of the selected period. "
                    "Past performance does not guarantee future results."
                )

            except Exception as e:
                st.error(f"Could not generate historical performance chart: {e}")

        with tab_mapping["Correlation"]:
            st.markdown("### Correlation Matrix")

            # Correlation heatmap
            if 'covariance_matrix' in result and result['covariance_matrix']:
                try:
                    cov_matrix = np.array(result['covariance_matrix'])
                    fig_corr = create_correlation_heatmap(cov_matrix, result['tickers'])
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
            st.markdown(f"**Cash Remaining:** ${result.get('leftover', 0):.2f}")

            if 'full_data_range' in result and result['full_data_range']:
                full_start, full_end = result['full_data_range']
                common_start, common_end = result.get('date_range', (full_start, full_end))
                if full_start != common_start:
                    st.markdown(f"**Price Data:** {full_start} to {full_end} (covariance)")
                    st.markdown(f"**Common Period:** {common_start} to {common_end} (backtest)")
                else:
                    st.markdown(f"**Analysis Period:** {common_start} to {common_end}")
            elif 'date_range' in result and result['date_range']:
                st.markdown(f"**Analysis Period:** {result['date_range'][0]} to {result['date_range'][1]}")

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
            st.error(f"Error generating PDF: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

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
