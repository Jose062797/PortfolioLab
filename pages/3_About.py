"""
About Page - PortfolioLab Platform
What the app is, which model to use, a glossary and an FAQ.
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
    <div style="margin-bottom: 2rem;">
        <h1 class="page-title">About PortfolioLab</h1>
        <p class="page-subtitle">Free, open-source software for learning portfolio optimization. It follows the Black-Litterman and Markowitz examples of the PyPortfolioOpt cookbook, on market data from Yahoo Finance.</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Which model?", "Glossary", "FAQ"])

    with tab1:
        col_m1, col_m2 = st.columns(2, gap="large")
        with col_m1:
            with st.container(border=True):
                st.markdown(
                    "#### Markowitz\n"
                    "Mean-variance optimization: the classic model behind the *efficient frontier*, "
                    "which earned Harry Markowitz a Nobel Prize.\n\n"
                    "**Use it when:**\n"
                    "- You want expected returns that come from price history alone.\n"
                    "- You have a risk or return target (e.g. the highest expected return with "
                    "volatility of at most 15%).\n"
                    "- You have no strong opinions about how particular assets will do.\n\n"
                    "*It can put too much into assets that did well in the past.*"
                )
        with col_m2:
            with st.container(border=True):
                st.markdown(
                    "#### Black-Litterman\n"
                    "A Bayesian model that starts from the market's own expectations, which "
                    "tempers Markowitz's tendency to concentrate the weights.\n\n"
                    "**Use it when:**\n"
                    "- You want expected returns anchored to market capitalizations rather than to "
                    "past returns.\n"
                    "- You have *views* about some assets (e.g. 'I think MSFT will return 15%').\n"
                    "- You want to start from market equilibrium (the market portfolio).\n\n"
                    "*Without views the expected returns are the market-implied ones, but the "
                    "optimizer then maximizes the Sharpe ratio against a 3% risk-free rate, with L2 "
                    "regularization. The weights can therefore differ a lot from market-cap weights, "
                    "and an asset whose implied return is below 3% can get none.*"
                )

    with tab2:
        st.markdown("""
        - **Volatility (risk)**: the annualized standard deviation of returns. Higher volatility means wilder price swings and higher risk.
        - **Sharpe ratio**: return above the risk-free rate for each unit of volatility, a measure of risk-adjusted return. The tools show an expected one (from the model's estimates) and a realized one (from the backtest). Above 1.0 is often considered good.
        - **L2 regularization (gamma)**: a penalty added during optimization that discourages putting most of the money into just 1 or 2 assets. Higher gamma spreads the weights more evenly.
        - **Market-implied returns**: the expected returns that would make today's market-cap weights the optimal portfolio, given the assets' risk (the starting point of Black-Litterman).
        - **Efficient frontier**: the portfolios with the highest expected return for each level of risk.
        """)

    with tab3:
        with st.expander("Where does the data come from?"):
            st.write("Prices come from Yahoo Finance through the open-source yfinance library. The Portfolio tool uses "
                     "daily closing prices adjusted for splits and dividends, on the dates when every asset has a price: "
                     "the full common history by default, or a custom date range. When one asset is much younger than "
                     "the others, that common history is shorter, and the results say so. The Stocks page charts quoted "
                     "closes, adjusted for splits only, as Yahoo does.")
        with st.expander("Is my portfolio data private?"):
            st.write("PortfolioLab does not store your inputs or results: they stay in the server's memory for your "
                     "session and are gone when it ends. To fetch prices, the ticker symbols you enter are sent to Yahoo "
                     "Finance. The hosted app runs on Streamlit Community Cloud, which keeps its own technical logs, and "
                     "the page fonts load from Google Fonts.")
        with st.expander("Why are portfolio weights changing across runs?"):
            st.write("Market data changes every day, so each run estimates from a slightly different history. Small "
                     "differences in the data window and in solver precision can also move the weights a little, "
                     "especially for highly correlated assets.")
        with st.expander("How do I know the numbers are right?"):
            st.write("The optimization follows the PyPortfolioOpt cookbook, and an automated test suite on GitHub "
                     "compares its results with the library's own on every change. The code is open source, so "
                     "anyone can check it.")

    # ── Render Footer ──
    from utils.styles import render_footer
    render_footer()


if __name__ == "__main__":
    main()
