"""
PortfolioLab - Multi-Tool Financial Platform
Home page: the front door (hero, example portfolios, the two tools, how it works)
"""

import logging
import os

import utils.ssl_fix  # noqa: F401 — applies SSL cert fix on import

import streamlit as st

# Configure logging for the Streamlit app
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
)

# Page configuration. Every page uses the brand favicon; a plain string that
# is not an emoji would be taken as an image URL.
st.set_page_config(
    page_title="PortfolioLab · Portfolio optimization lab",
    page_icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "favicon.png"),
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Critical CSS: hide sidebar/chrome IMMEDIATELY to prevent flash on navigation
from utils.styles import inject_critical_css, inject_styles, render_navbar
inject_critical_css()
inject_styles()
render_navbar(active_page="home")

from core.constants import goal_text  # noqa: E402
from core.example_market import EXAMPLE_PORTFOLIOS, example_ohlcv, load_example  # noqa: E402
from utils.visualizations import create_allocation_pie, create_price_chart  # noqa: E402

# The tool cards show the charts the tools draw, built by the same functions
# from example data (core/example_market.py). Only the height changes, to fit
# the card, and the Plotly toolbar is hidden.
CHART_CONFIG = {"displayModeBar": False, "scrollZoom": False}
PIE_HEIGHT = 320
# The price chart matches the pie plus the figures row under it, so the text
# of both tool cards starts at the same height.
PRICE_HEIGHT = PIE_HEIGHT + 22

STEPS = [
    ("Pick your assets",
     "Up to 20 stocks, ETFs or crypto, and the amount you want to invest."),
    ("Choose a goal",
     "The lowest risk, the best return for the risk, or a limit of your own. "
     "With Black-Litterman you can add what you expect from some assets."),
    ("See the result",
     "The weights, the whole shares to buy, a backtest against the S&P 500 and a PDF report."),
]


@st.cache_data(show_spinner=False)
def _example() -> dict:
    """The engine's result on the made-up assets (core/example_market.py)."""
    return load_example()


@st.cache_data(show_spinner=False)
def _example_prices():
    """One year of made-up daily prices for the Stocks card."""
    return example_ohlcv()


def _pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _goal(example: dict) -> str:
    """An example's goal in the words the Portfolio form uses."""
    return goal_text(example["objective"], example.get("target_volatility"), example.get("target_return"))


def _hero() -> None:
    """Headline, what the app does and the two ways in.

    Stocks comes first, as in the tool cards below: look an asset up, then
    build the portfolio (the user's reading order, 2026-09-27). Portfolio
    keeps the primary style.
    """
    st.markdown("""
    <div class="bl-hero">
        <h1>Build and test a portfolio in minutes</h1>
        <p class="bl-lead">Enter a few tickers and choose a goal. PortfolioLab finds the optimal weights with Markowitz or Black-Litterman, shows how they would have done, and turns them into whole shares for your budget.</p>
        <div class="bl-ctas">
            <a class="bl-btn bl-btn-secondary" href="./Stocks" target="_self">Explore a stock</a>
            <a class="bl-btn bl-btn-primary" href="./Portfolio" target="_self">Build a portfolio</a>
        </div>
        <p class="bl-hero-meta">Free and open source · Market data from Yahoo Finance · For learning, not investment advice</p>
    </div>
    """, unsafe_allow_html=True)


def _examples() -> None:
    """Example portfolios: each card opens the Portfolio form filled in."""
    # Relative links, like the navbar's; the Portfolio page reads ?example=
    cards = "".join(
        f'<a class="bl-example" href="./Portfolio?example={key}" target="_self">'
        f'<span class="bl-example-title">{example["title"]}</span>'
        '<span class="bl-chips">'
        + "".join(f'<span class="bl-chip">{t}</span>' for t in example["tickers"])
        + '</span>'
        f'<span class="bl-example-goal">Goal: {_goal(example)}</span>'
        '<span class="bl-example-open">Open in Portfolio <span aria-hidden="true">&rarr;</span></span>'
        '</a>'
        for key, example in EXAMPLE_PORTFOLIOS.items()
    )
    st.markdown(f"""
    <div class="bl-section-head">
        <h2>Try an example</h2>
        <p>Each one opens the Portfolio tool with the form filled in. Press Run to see the result on today's data.</p>
    </div>
    <div class="bl-examples">{cards}</div>
    """, unsafe_allow_html=True)


def _tools(ex: dict) -> None:
    """The two tool cards, each topped by the tool's own chart on example data."""
    st.markdown("""
    <div class="bl-section-head">
        <h2>Two tools</h2>
        <p>Look up one asset, or build a whole portfolio.</p>
    </div>
    """, unsafe_allow_html=True)

    # The Stocks page's price chart in its default view (1Y, Line)
    price_fig = create_price_chart(_example_prices(), "Example", "Line")
    price_fig.update_layout(height=PRICE_HEIGHT)

    # The Portfolio page's allocation chart and headline figures
    portfolio = ex["portfolio"]
    pie_fig = create_allocation_pie(portfolio["weights"])
    pie_fig.update_layout(height=PIE_HEIGHT)

    # Card and picture area are containers (they hold charts);
    # key="bl-card-…" and "bl-visual-…" are styled in utils/styles.py.
    # Links are relative for the same reason as the navbar's.
    col1, col2 = st.columns(2, gap="large")

    with col1:
        with st.container(key="bl-card-stocks"):
            with st.container(key="bl-visual-stocks"):
                st.markdown(
                    '<div class="bl-fig-head"><span>Price and volume, one year</span>'
                    '<span class="bl-tag">Example</span></div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(price_fig, width="stretch", config=CHART_CONFIG)
            st.markdown("""
            <div class="bl-tool-body">
                <h3>Stocks</h3>
                <p>Charts, returns and key figures for any Yahoo Finance symbol: stocks, ETFs, crypto and indices.</p>
                <a class="bl-tool-link" href="./Stocks" target="_self">Open Stocks <span aria-hidden="true">&rarr;</span></a>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        with st.container(key="bl-card-portfolio"):
            with st.container(key="bl-visual-portfolio"):
                st.markdown(
                    '<div class="bl-fig-head"><span>Allocation</span>'
                    '<span class="bl-tag">Example</span></div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(pie_fig, width="stretch", config=CHART_CONFIG)
                # Same figures and formats as the Portfolio page's metric cards
                st.markdown(
                    '<div class="bl-metrics">'
                    f'<span>Expected return <b>{_pct(portfolio["return"])}</b></span>'
                    f'<span>Volatility <b>{_pct(portfolio["volatility"])}</b></span>'
                    f'<span>Sharpe ratio <b>{portfolio["sharpe"]:.3f}</b></span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("""
            <div class="bl-tool-body">
                <h3>Portfolio</h3>
                <p>Optimal weights with Markowitz or Black-Litterman, whole shares for your budget, a backtest and a PDF report.</p>
                <a class="bl-tool-link" href="./Portfolio" target="_self">Open Portfolio <span aria-hidden="true">&rarr;</span></a>
            </div>
            """, unsafe_allow_html=True)


def _how_it_works() -> None:
    """The three steps of the Portfolio tool."""
    steps_html = "".join(
        f'<div class="bl-step"><span class="bl-step-num">{n}</span>'
        f'<h3>{title}</h3><p>{text}</p></div>'
        for n, (title, text) in enumerate(STEPS, start=1)
    )
    st.markdown(f"""
    <div class="bl-section-head">
        <h2>How it works</h2>
    </div>
    <div class="bl-steps">{steps_html}</div>
    """, unsafe_allow_html=True)


def main():
    """Home page: the front door of PortfolioLab."""
    _hero()
    _examples()
    _tools(_example())
    _how_it_works()

    # ── Render Footer ──
    from utils.styles import render_footer
    render_footer()


if __name__ == "__main__":
    main()
