"""
About Page - PortfolioLab Platform
Modern design with top navbar, no sidebar
"""

import os

import streamlit as st

st.set_page_config(
    page_title="About · PortfolioLab",
    page_icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "favicon.png"),
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Critical CSS: hide sidebar/chrome IMMEDIATELY to prevent flash on navigation
from utils.styles import inject_critical_css, inject_styles, render_navbar
inject_critical_css()
inject_styles()
render_navbar(active_page="about")


def main():
    # ── Page Header ──
    st.markdown("""
    <div class="bl-band">
        <div class="bl-band-inner bl-animate">
            <p class="bl-eyebrow">About PortfolioLab</p>
            <h1>Portfolio optimization <span class="accent">you can verify.</span></h1>
            <p class="bl-lead">PortfolioLab is free, open-source software for learning portfolio optimization. It implements the Black-Litterman and Markowitz models of the PyPortfolioOpt cookbook on market data from Yahoo Finance, and an automated test suite checks its results against the library on every change.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── How it works ──
    # Same text as the landing page (docs/index.html): keep both in sync.
    st.markdown("""
    <div class="bl-block-head">
        <p class="bl-eyebrow">How it works</p>
        <h2>From tickers to shares in four steps</h2>
        <p class="bl-block-lead">This is the path the Portfolio tool follows, with either model.</p>
    </div>
    <div class="bl-steps">
        <div class="bl-step">
            <span class="bl-step-num">STEP 1</span>
            <h3>Pick the assets</h3>
            <p>Enter 2 to 20 tickers and your budget. Prices come from Yahoo Finance, adjusted for splits and dividends.</p>
        </div>
        <div class="bl-step">
            <span class="bl-step-num">STEP 2</span>
            <h3>Say what you expect</h3>
            <p>With Black-Litterman, give an expected return and a range for the assets you have a view on. With Markowitz, choose one of four objectives.</p>
        </div>
        <div class="bl-step">
            <span class="bl-step-num">STEP 3</span>
            <h3>Optimize</h3>
            <p>The engine estimates returns and a shrunk covariance matrix, then finds the weights that sit on the efficient frontier.</p>
        </div>
        <div class="bl-step">
            <span class="bl-step-num">STEP 4</span>
            <h3>Allocate and report</h3>
            <p>Weights become whole shares for your budget. Check the backtest, then download the PDF report.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Verification ──
    # Same facts as the landing page. The numbers are claims about the test
    # suite and CI: update them here and in docs/index.html together.
    st.markdown("""
    <div class="bl-block-head">
        <p class="bl-eyebrow">Verification</p>
        <h2>Checked against the reference on every change</h2>
        <p class="bl-block-lead">PortfolioLab follows the PyPortfolioOpt cookbook. An automated suite compares its results with the library's own, and a change that moves any number makes the suite fail.</p>
    </div>
    <div class="bl-facts">
        <div class="bl-fact">
            <h3>Identical to PyPortfolioOpt</h3>
            <p>Six optimization paths, Black-Litterman with views included, produce exactly the library's weights and metrics.</p>
        </div>
        <div class="bl-fact">
            <h3>Frozen snapshots</h3>
            <p>Exact results are stored and compared on each run, so a dependency upgrade cannot shift them unnoticed.</p>
        </div>
        <div class="bl-fact">
            <h3>MIT reference cases</h3>
            <p>Six scenarios from MIT course material, reproduced with real market data.</p>
        </div>
        <div class="bl-fact">
            <h3>Tested on every push</h3>
            <p>108 automated tests run on Python 3.12 and 3.14 for every change.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Educational Resources ──
    st.markdown("""
    <div class="bl-block-head">
        <p class="bl-eyebrow">Learn</p>
        <h2>Financial Glossary &amp; Methodology</h2>
        <p class="bl-block-lead">Understand the concepts behind professional portfolio management</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Model Comparison", "Financial Glossary", "FAQ"])

    with tab1:
        st.markdown("### Which Optimization Model Should I Use?")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.info("**Markowitz (Mean-Variance Optimization)**\n\n"
                    "The Nobel Prize-winning classic model that builds an *Efficient Frontier*.\n\n"
                    "**Use when:**\n"
                    "- You want a purely data-driven approach based solely on historical prices.\n"
                    "- You have specific risk or return targets (e.g., maximize return for exactly 15% volatility).\n"
                    "- You don't have strong subjective opinions about future asset performance.\n\n"
                    "*Warning: Traditional MVO can over-allocate to assets that performed well in the past.*")
        with col_m2:
            st.success("**Black-Litterman Model**\n\n"
                       "A Bayesian approach that addresses Markowitz's tendency to concentrate the weights.\n\n"
                       "**Use when:**\n"
                       "- You want a highly diversified, robust portfolio that doesn't overreact to past anomalies.\n"
                       "- You have specific *views* or expectations about certain assets (e.g., 'I think MSFT will return 15%').\n"
                       "- You want a professional starting point based on market equilibrium (the market portfolio).\n\n"
                       "*Note: without custom views the model uses the market-implied returns, so the portfolio starts from market-cap weights.*")

    with tab2:
        st.markdown("### Key Financial Terms")
        st.markdown("""
        - **Volatility (Risk)**: The annualized standard deviation of returns. Higher volatility means wilder price swings and higher risk.
        - **Sharpe Ratio**: A measure of risk-adjusted return. It tells you how much excess return you are getting for the extra volatility you endure. A Sharpe ratio > 1.0 is considered good.
        - **L2 Gamma (Regularization)**: A mathematical penalty applied during optimization to prevent the model from putting all your money into just 1 or 2 assets. Higher Gamma = more diversified.
        - **Market Implied Returns**: The returns that the overall market *expects* assets to have, based on their current market capitalization and risk (used as the baseline in Black-Litterman).
        - **Efficient Frontier**: A curve showing the set of optimal portfolios that offer the highest expected return for a defined level of risk.
        """)

    with tab3:
        st.markdown("### Frequently Asked Questions")
        with st.expander("Where does the data come from?"):
            st.write("Prices come from Yahoo Finance through the open-source yfinance library, adjusted for splits and dividends. By default the Portfolio tool uses the full daily history available for each asset; you can also set a custom date range.")
        with st.expander("Is my portfolio data private?"):
            st.write("PortfolioLab does not save your inputs or results: they live in memory for your session only and are gone when it ends. To fetch prices, the ticker symbols you enter are sent to Yahoo Finance.")
        with st.expander("Why are portfolio weights changing across runs?"):
            st.write("Live market data changes daily. Additionally, minor differences in historical data bounds and solver precision can result in slightly different weights, especially for highly correlated assets.")

    # ── Render Footer ──
    from utils.styles import render_footer
    render_footer()


if __name__ == "__main__":
    main()
