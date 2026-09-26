"""
PortfolioLab - Multi-Tool Financial Platform
Home page: the front door (hero with Fig. 1, tools, method, verification)
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

from core.constants import MIN_WEIGHT_THRESHOLD  # noqa: E402
from core.example_market import example_ohlcv, load_example  # noqa: E402
from utils.visualizations import (  # noqa: E402
    BRAND_SEQUENCE,
    create_allocation_pie,
    create_efficient_frontier_chart,
    create_price_chart,
)

# Claims about the project shown on this page (hero stats and the
# verification facts). Keep them true: update them, and the README, whenever
# the test suite or CI changes.
TEST_COUNT = 130

# Every chart on this page is a chart the tools draw, built by the same
# function from example data (core/example_market.py). Only the height
# changes, to fit the page, and the Plotly toolbar is hidden.
CHART_CONFIG = {"displayModeBar": False, "scrollZoom": False}
FRONTIER_HEIGHT = 440
PIE_HEIGHT = 380
# The price chart matches the pie plus the metrics row under it, so the text
# of both tool cards starts at the same height.
PRICE_HEIGHT = PIE_HEIGHT + 22

# Icons of the four method steps (decorative; stroke follows the text color)
STEP_ICONS = [
    '<svg width="46" height="24" viewBox="0 0 46 24" fill="none"><rect x="1" y="3" width="20" height="8" rx="4" stroke="currentColor" stroke-width="1.4"/><rect x="25" y="3" width="20" height="8" rx="4" stroke="currentColor" stroke-width="1.4"/><rect x="9" y="14" width="20" height="8" rx="4" fill="currentColor" fill-opacity=".18" stroke="currentColor" stroke-width="1.4"/></svg>',
    '<svg width="46" height="24" viewBox="0 0 46 24" fill="none"><line x1="3" y1="12" x2="43" y2="12" stroke="currentColor" stroke-opacity=".35" stroke-width="2" stroke-linecap="round"/><line x1="14" y1="12" x2="34" y2="12" stroke="currentColor" stroke-width="3" stroke-linecap="round"/><circle cx="24" cy="12" r="4.5" fill="currentColor"/><line x1="14" y1="6" x2="14" y2="18" stroke="currentColor" stroke-width="1.4"/><line x1="34" y1="6" x2="34" y2="18" stroke="currentColor" stroke-width="1.4"/></svg>',
    '<svg width="46" height="26" viewBox="0 0 46 26" fill="none"><path d="M5 22 C 8 9, 18 4, 42 3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="16" cy="8.6" r="3.6" fill="#10B981"/><circle cx="9" cy="17" r="1.3" fill="currentColor" fill-opacity=".5"/><circle cx="22" cy="14" r="1.3" fill="currentColor" fill-opacity=".5"/><circle cx="30" cy="11" r="1.3" fill="currentColor" fill-opacity=".5"/><circle cx="17" cy="19" r="1.3" fill="currentColor" fill-opacity=".5"/></svg>',
    '<svg width="46" height="26" viewBox="0 0 46 26" fill="none"><rect x="2" y="14" width="7" height="10" rx="1.5" fill="currentColor"/><rect x="11" y="8" width="7" height="16" rx="1.5" fill="currentColor" fill-opacity=".7"/><rect x="20" y="11" width="7" height="13" rx="1.5" fill="currentColor" fill-opacity=".45"/><path d="M33 3h7l4 4v16a1 1 0 0 1-1 1H33a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" stroke="currentColor" stroke-width="1.4"/><path d="M35 12h6M35 16h6M35 20h4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
]

STEPS = [
    ("Pick the assets",
     "Enter 2 to 20 tickers and your budget. Prices come from Yahoo Finance, adjusted for splits and dividends."),
    ("Say what you expect",
     "With Black-Litterman, give an expected return and a range for the assets you have a view on. "
     "With Markowitz, choose one of four objectives."),
    ("Optimize",
     "The engine estimates expected returns (blending in your views, with Black-Litterman) and a shrunk "
     "covariance matrix, then solves for the optimal weights with PyPortfolioOpt."),
    ("Allocate and report",
     "Weights become whole shares for your budget. Check the backtest, then download the PDF report."),
]


@st.cache_data(show_spinner=False)
def _example() -> dict:
    """The engine's results on the example assets (core/example_market.py)."""
    return load_example()


@st.cache_data(show_spinner=False)
def _example_prices():
    """One year of made-up daily prices for the Stocks card."""
    return example_ohlcv()


def _pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _hero(ex: dict) -> None:
    """Navy hero: headline, calls to action and stats beside Fig. 1."""
    portfolio = ex["portfolio"]
    # Exactly what the Portfolio page's Efficient Frontier tab draws for a
    # run: the engine's frontier data plus the chosen portfolio's marker.
    fig = create_efficient_frontier_chart(ex["ef_data"], selected_portfolio={
        "ret": portfolio["return"],
        "risk": portfolio["volatility"],
        "sharpe": portfolio["sharpe"],
        "label": "Portfolio",
    })
    # The page draws it 800 px wide (width='content'); here it takes the
    # card's width instead.
    fig.update_layout(height=FRONTIER_HEIGHT, width=None)

    # A container, not HTML: the Plotly chart is a Streamlit element.
    # key="bl-hero" gives it the CSS class .st-key-bl-hero (utils/styles.py).
    with st.container(key="bl-hero"):
        left, right = st.columns([1.05, 1], gap="large", vertical_alignment="center")
        with left:
            st.markdown(f"""
            <div class="bl-dark bl-hero-copy bl-animate">
                <p class="bl-eyebrow">Portfolio optimization lab</p>
                <h1>Build optimal portfolios. <span class="accent">Verify every number.</span></h1>
                <p class="bl-lead">Black-Litterman and Markowitz optimization on market data from Yahoo Finance, with interactive charts and a PDF report. Results match PyPortfolioOpt, the reference library, to the last digit.</p>
                <div class="bl-ctas">
                    <a class="bl-btn bl-btn-primary" href="./Portfolio" target="_self">Build a portfolio &rarr;</a>
                    <a class="bl-btn bl-btn-ondark" href="./Stocks" target="_self">Explore a stock</a>
                </div>
                <p class="bl-hero-meta">Free and open source (MIT). For learning, not investment advice.</p>
                <dl class="bl-band-stats">
                    <div><dt>2</dt><dd>optimization models</dd></div>
                    <div><dt>4</dt><dd>Markowitz objectives</dd></div>
                    <div><dt>{TEST_COUNT}</dt><dd>automated tests</dd></div>
                    <div><dt>6</dt><dd>paths identical to PyPortfolioOpt</dd></div>
                </dl>
            </div>
            """, unsafe_allow_html=True)
        with right:
            with st.container(key="bl-figure"):
                st.markdown(
                    '<div class="bl-fig-head"><span><b>Fig. 1</b> · Efficient frontier</span>'
                    '<span class="bl-tag">Example data</span></div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)
                st.markdown(
                    '<p class="bl-fig-caption">Five made-up assets, A to E, run through the Portfolio '
                    f'tool\'s engine and drawn with its own chart: Markowitz, "{ex["objective"]}" with a '
                    f'{_pct(ex["target_volatility"], 0)} target volatility, {_pct(ex["rf"], 0)} risk-free rate. '
                    'Hover to read any point.</p>',
                    unsafe_allow_html=True,
                )


def _tools(ex: dict) -> None:
    """The two tool cards, each topped by the tool's own chart on example data."""
    st.markdown("""
    <div class="bl-block-head">
        <p class="bl-eyebrow">The tools</p>
        <h2>Explore a market, then build a portfolio</h2>
        <p class="bl-block-lead">Two tools on the same Yahoo Finance data. Start with one asset, or go straight to a full allocation.</p>
    </div>
    """, unsafe_allow_html=True)

    # The Stocks page's price chart in its default view (1Y, Line)
    price_fig = create_price_chart(_example_prices(), "Example", "Line")
    price_fig.update_layout(height=PRICE_HEIGHT)

    # The Portfolio page's Allocation tab: pie and headline metrics
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
                    '<div class="bl-fig-head"><span>Price and volume · 1Y · Line</span>'
                    '<span class="bl-tag">Example data</span></div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(price_fig, width="stretch", config=CHART_CONFIG)
            st.markdown("""
            <div class="bl-tool-body">
                <h3>Stocks</h3>
                <p>Charts and statistics for any Yahoo Finance symbol: stocks, ETFs, crypto and indices.</p>
                <ul class="bl-checks">
                    <li>Line or candlestick charts with volume, from one day to the full history</li>
                    <li>Returns over eight periods, from one day to the full history</li>
                    <li>Key statistics for each asset type, including the analysts' one-year price target for stocks</li>
                    <li>For stocks, price returns against the S&amp;P 500 and quarterly revenue and earnings</li>
                </ul>
                <a class="bl-tool-link" href="./Stocks" target="_self">Open Stocks &rarr;</a>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        with st.container(key="bl-card-portfolio"):
            with st.container(key="bl-visual-portfolio"):
                st.markdown(
                    '<div class="bl-fig-head"><span>Allocation · Fig. 1 portfolio</span>'
                    '<span class="bl-tag">Example data</span></div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(pie_fig, width="stretch", config=CHART_CONFIG)
                # Same labels and formats as the Portfolio page's metric cards
                st.markdown(
                    '<div class="bl-metrics">'
                    f'<span>Expected Return <b>{_pct(portfolio["return"])}</b></span>'
                    f'<span>Volatility <b>{_pct(portfolio["volatility"])}</b></span>'
                    f'<span>Sharpe Ratio <b>{portfolio["sharpe"]:.3f}</b></span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("""
            <div class="bl-tool-body">
                <h3>Portfolio</h3>
                <p>Optimize with Black-Litterman or Markowitz, then turn the weights into whole shares for your budget.</p>
                <ul class="bl-checks">
                    <li>Your own return views, each with a range that sets its confidence (Black-Litterman)</li>
                    <li>Four objectives, from minimum variance to a target return (Markowitz)</li>
                    <li>Backtest and correlation charts, plus the efficient frontier (Markowitz) or prior and posterior returns (Black-Litterman)</li>
                    <li>A PDF report of the full analysis</li>
                </ul>
                <a class="bl-tool-link" href="./Portfolio" target="_self">Open Portfolio &rarr;</a>
            </div>
            """, unsafe_allow_html=True)


def _how_it_works() -> None:
    """The four steps the Portfolio tool follows."""
    steps_html = "".join(
        f'<div class="bl-step"><div class="bl-step-top"><span class="bl-step-num">STEP {n}</span>'
        f'<span class="bl-step-icon" aria-hidden="true">{icon}</span></div>'
        f'<h3>{title}</h3><p>{text}</p></div>'
        for n, ((title, text), icon) in enumerate(zip(STEPS, STEP_ICONS), start=1)
    )
    st.markdown(f"""
    <div class="bl-block-head" style="margin-top: 3.5rem;">
        <p class="bl-eyebrow">How it works</p>
        <h2>From tickers to shares in four steps</h2>
        <p class="bl-block-lead">This is the path the Portfolio tool follows, with either model.</p>
    </div>
    <div class="bl-steps">{steps_html}</div>
    """, unsafe_allow_html=True)


def _difference(a: float, b: float) -> str:
    """Absolute difference for the parity table: '0' when the numbers are identical."""
    d = abs(a - b)
    return '<span class="zero">0</span>' if d == 0 else f"{d:.1e}"


def _parity_table(ex: dict) -> str:
    """Fig. 1's portfolio as solved by the engine and by PyPortfolioOpt directly."""
    engine, reference = ex["portfolio"], ex["reference"]
    weights = engine["weights"]
    # The pie's colors: create_allocation_pie hands out BRAND_SEQUENCE in this order
    shown = [t for t, w in weights.items() if w > MIN_WEIGHT_THRESHOLD]
    colors = dict(zip(shown, BRAND_SEQUENCE))

    rows = "".join(
        f'<tr><td><i class="bl-dot" style="background:{colors.get(t, "#CBD5E1")}"></i>{t}</td>'
        f'<td>{_pct(weights[t], 3)}</td><td>{_pct(reference["weights"][t], 3)}</td>'
        f'<td>{_difference(weights[t], reference["weights"][t])}</td></tr>'
        for t in sorted(weights, key=weights.get, reverse=True)
    )
    metrics = [
        ("Expected Return", "return", lambda v: _pct(v, 4)),
        ("Volatility", "volatility", lambda v: _pct(v, 4)),
        ("Sharpe Ratio", "sharpe", lambda v: f"{v:.5f}"),
    ]
    rows_metrics = "".join(
        f'<tr><td>{label}</td><td>{fmt(engine[key])}</td><td>{fmt(reference[key])}</td>'
        f'<td>{_difference(engine[key], reference[key])}</td></tr>'
        for label, key, fmt in metrics
    )
    return (
        '<div class="bl-parity-scroll"><table class="bl-parity-table">'
        f'<thead><tr><th></th><th>PortfolioLab</th><th>PyPortfolioOpt {ex["pypfopt_version"]}</th>'
        '<th>Difference</th></tr></thead>'
        f'<tbody><tr class="bl-group"><td colspan="4">Weights</td></tr>{rows}'
        f'<tr class="bl-group"><td colspan="4">Metrics</td></tr>{rows_metrics}</tbody></table></div>'
    )


def _verification(ex: dict) -> None:
    """Navy band: how the results are checked, with a real parity table."""
    st.markdown(f"""
    <div class="bl-band bl-verify">
        <div class="bl-band-inner bl-dark bl-verify-grid">
            <div>
                <p class="bl-eyebrow">Verification</p>
                <h2>Checked against the reference on every change</h2>
                <p class="bl-lead">PortfolioLab follows the PyPortfolioOpt cookbook. An automated suite compares its results with the library's own and fails if a change moves an optimization result.</p>
                <dl class="bl-facts-dark">
                    <div><dt>Identical to PyPortfolioOpt</dt><dd>Six optimization paths, Black-Litterman with views included, give exactly the library's weights and metrics.</dd></div>
                    <div><dt>Frozen snapshots</dt><dd>The weights and metrics of reference runs are stored and checked on every run, so a dependency upgrade cannot shift them unnoticed.</dd></div>
                    <div><dt>Formulas checked by hand</dt><dd>Backtest metrics such as the annualized Sharpe and Sortino ratios are compared with values computed by hand.</dd></div>
                    <div><dt>Tested on every push</dt><dd>{TEST_COUNT} automated tests run on Python 3.12 and 3.14 for every change.</dd></div>
                </dl>
            </div>
            <div class="bl-parity">
                <div class="bl-fig-head"><span><b>Parity check</b> · Fig. 1 portfolio</span><span class="bl-tag">Example data</span></div>
                {_parity_table(ex)}
                <div class="bl-parity-eq">Same inputs, same weights, same metrics.</div>
                <p class="bl-parity-note">The left column is PortfolioLab's engine, the right one PyPortfolioOpt called directly, both on the five example assets of Fig. 1. A test solves both again on every push. The parity suite itself runs six optimization paths on synthetic market data with a fixed seed.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Home page: the front door of PortfolioLab."""
    ex = _example()
    _hero(ex)
    _tools(ex)
    _how_it_works()
    _verification(ex)

    # ── Render Footer ──
    from utils.styles import render_footer
    render_footer()


if __name__ == "__main__":
    main()
