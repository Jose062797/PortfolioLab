"""
About Page - PortfolioLab Platform
Modern design with top navbar, no sidebar
"""

import streamlit as st

st.set_page_config(
    page_title="About - PortfolioLab",
    page_icon="BL",
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
    <div style="background:linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
                border-radius:16px; margin-bottom:2rem;">
        <div class="bl-hero bl-animate">
            <h1>About PortfolioLab</h1>
            <p>Professional portfolio optimization and analysis tools for investors</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Platform Introduction ──
    st.markdown("""
    <div class="bl-info bl-animate">
        <strong>PortfolioLab</strong> is a comprehensive platform for portfolio optimization and financial analysis.
        Built with modern financial libraries and battle-tested algorithms, it provides professional-grade tools
        for portfolio construction, risk management, and performance analysis&mdash;all running locally to keep your data private.
    </div>
    """, unsafe_allow_html=True)

    # ── Educational Resources ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="bl-section-header">
        <h2>Financial Glossary & Methodology</h2>
        <p>Understand the concepts behind professional portfolio management</p>
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
                       "A modern Bayesian approach that solves Markowitz's concentration issues.\n\n"
                       "**Use when:**\n"
                       "- You want a highly diversified, robust portfolio that doesn't overreact to past anomalies.\n"
                       "- You have specific *views* or expectations about certain assets (e.g., 'I think MSFT will return 15%').\n"
                       "- You want a professional starting point based on market equilibrium (the market portfolio).\n\n"
                       "*Note: Even without custom views, BL provides a highly balanced portfolio.*")

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
            st.write("All historical price data is fetched in real-time from reliable market data providers. We typically use 3 to 10 years of daily historical data to calculate covariance matrices and expected returns.")
        with st.expander("Is my portfolio data private?"):
            st.write("Yes, 100% private. PortfolioLab runs the optimization math directly in the current session. No financial data, portfolio sizes, or investment views are stored or sent to external databases.")
        with st.expander("Why are portfolio weights changing across runs?"):
            st.write("Live market data changes daily. Additionally, minor differences in historical data bounds and solver precision can result in slightly different weights, especially for highly correlated assets.")

    # ── Render Footer ──
    from utils.styles import render_footer
    render_footer()


if __name__ == "__main__":
    main()
