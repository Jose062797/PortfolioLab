"""
PortfolioLab - Multi-Tool Financial Platform
Modern tool hub landing page
"""

import logging
import utils.ssl_fix  # noqa: F401 — applies SSL cert fix on import

import streamlit as st

# Configure logging for the Streamlit app
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
)

# Page configuration
st.set_page_config(
    page_title="PortfolioLab - Portfolio Tools",
    page_icon="BL",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Critical CSS: hide sidebar/chrome IMMEDIATELY to prevent flash on navigation
from utils.styles import inject_critical_css, inject_styles, render_navbar
inject_critical_css()
inject_styles()
render_navbar(active_page="home")


def main():
    """Main landing page - tool hub with card-based interface."""

    # ── Hero Section ──
    from utils.styles import get_base64_of_bin_file
    
    # Pre-load base64 images for the layout
    hero_bg = get_base64_of_bin_file("static/hero_background.png")
    stocks_thumb = get_base64_of_bin_file("static/thumbnail_stocks_blue.png")
    port_thumb = get_base64_of_bin_file("static/thumbnail_portfolio_blue.png")

    st.markdown(f"""
    <div class="bl-hero-bg" style="background-image: url('data:image/png;base64,{hero_bg}');">
        <div class="bl-hero-overlay"></div>
        <div class="bl-hero bl-animate">
            <h1>PortfolioLab</h1>
            <p>
                Professional-grade portfolio optimization, analysis, and visualization tools. Choose a tool below to get started.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tools Section (No Header) ──

    # ── Tool Image Cards ──
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(f"""
        <a href="/Stocks" target="_self" class="bl-image-card bl-animate bl-animate-delay-1">
            <div class="bl-image-card-header-wrap">
                <div class="bl-image-card-header" style="background-image: url('data:image/png;base64,{stocks_thumb}');"></div>
            </div>
            <div class="bl-image-card-body">
                <h3>Stocks</h3>
                <p>Real-time charts and analysis for any stock, ETF, or index.</p>
                <ul class="bl-image-card-features">
                    <li>&#10003; Interactive candlestick charts</li>
                    <li>&#10003; Key metrics & fundamentals</li>
                    <li>&#10003; Real-time market data</li>
                    <li>&#10003; Period returns analysis</li>
                </ul>
                <div class="bl-image-card-btn">Open Tool</div>
            </div>
        </a>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <a href="/Portfolio" target="_self" class="bl-image-card bl-animate bl-animate-delay-2">
            <div class="bl-image-card-header-wrap">
                <div class="bl-image-card-header" style="background-image: url('data:image/png;base64,{port_thumb}');"></div>
            </div>
            <div class="bl-image-card-body">
                <h3>Portfolio</h3>
                <p>Build optimal portfolios using Black-Litterman or Markowitz models.</p>
                <ul class="bl-image-card-features">
                    <li>&#10003; Custom investment views (BL method)</li>
                    <li>&#10003; Markowitz MVO & Efficient Frontier</li>
                    <li>&#10003; Interactive risk/return visualizations</li>
                    <li>&#10003; PDF export reports</li>
                </ul>
                <div class="bl-image-card-btn">Open Tool</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    # ── Stats Row ──
    st.markdown("""
    <div class="bl-stats bl-animate">
        <div class="bl-stat">
            <div class="bl-stat-value">2</div>
            <div class="bl-stat-label">Financial tools</div>
        </div>
        <div class="bl-stat">
            <div class="bl-stat-value">30Y+</div>
            <div class="bl-stat-label">Historical data</div>
        </div>
        <div class="bl-stat">
            <div class="bl-stat-value">150k+</div>
            <div class="bl-stat-label">Stocks &amp; assets</div>
        </div>
        <div class="bl-stat">
            <div class="bl-stat-value">PDF</div>
            <div class="bl-stat-label">Export reports</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


    # ── Render Footer ──
    from utils.styles import render_footer
    render_footer()


if __name__ == "__main__":
    main()
