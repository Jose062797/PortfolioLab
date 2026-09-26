"""
PortfolioLab - Multi-Tool Financial Platform
Home page: the public front door (hero with Fig. 1, tools, method, verification)
"""

import logging
import os
import random

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

from core.example_market import load_example_frontier  # noqa: E402
from utils.visualizations import create_example_frontier_figure  # noqa: E402

# Claims about the project shown on this page (hero stats, the verification
# facts and the parity schematic). Keep them true: update them, and the README,
# whenever the test suite or CI changes.
TEST_COUNT = 110

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
     "The engine estimates returns and a shrunk covariance matrix, then finds the weights that sit on "
     "the efficient frontier."),
    ("Allocate and report",
     "Weights become whole shares for your budget. Check the backtest, then download the PDF report."),
]


@st.cache_data(show_spinner=False)
def _example_market() -> dict:
    """Fig. 1 data (core/example_market.py), built once per server process."""
    return load_example_frontier()


def _pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def _example_candles_html(count: int = 32, seed: int = 7) -> str:
    """
    Decorative candlesticks for the Stocks card, drawn with plain HTML.

    The prices are a seeded random walk (example data, not market data), so
    the picture is the same on every run. Each candle is a wick (<i>) and a
    body (<b>), positioned in percent of the strip height by the CSS in
    utils/styles.py (.bl-candles).
    """
    rng = random.Random(seed)
    candles, price = [], 100.0
    for _ in range(count):
        open_ = price
        close = open_ * (1 + rng.gauss(0.003, 0.018))
        high = max(open_, close) * (1 + abs(rng.gauss(0, 0.006)))
        low = min(open_, close) * (1 - abs(rng.gauss(0, 0.006)))
        candles.append((open_, high, low, close))
        price = close

    top = max(c[1] for c in candles)
    span = top - min(c[2] for c in candles)

    def pct(value: float) -> float:
        """Distance from the top of the strip, in percent of its height."""
        return (top - value) / span * 100

    html = ""
    for open_, high, low, close in candles:
        direction = "up" if close >= open_ else "dn"
        body_top = pct(max(open_, close))
        body_height = max(pct(min(open_, close)) - body_top, 1.5)
        html += (
            f'<span class="{direction}">'
            f'<i style="top:{pct(high):.1f}%;height:{pct(low) - pct(high):.1f}%"></i>'
            f'<b style="top:{body_top:.1f}%;height:{body_height:.1f}%"></b>'
            '</span>'
        )
    return html


def _hero(data: dict) -> None:
    """Navy hero: headline, calls to action and stats beside Fig. 1."""
    # A container, not HTML: the Plotly chart is a Streamlit element.
    # key="bl-hero" gives it the CSS class .st-key-bl-hero (utils/styles.py).
    with st.container(key="bl-hero"):
        left, right = st.columns([1.05, 1], gap="large", vertical_alignment="center")
        with left:
            st.markdown(f"""
            <div class="bl-dark bl-hero-copy bl-animate">
                <p class="bl-eyebrow">Portfolio optimization lab</p>
                <h1>Build optimal portfolios. <span class="accent">Verify every number.</span></h1>
                <p class="bl-lead">Black-Litterman and Markowitz optimization on live market data, with interactive charts and a PDF report. Results match PyPortfolioOpt, the reference library, to the last digit.</p>
                <div class="bl-ctas">
                    <a class="bl-btn bl-btn-primary" href="./Portfolio" target="_self">Build a portfolio &rarr;</a>
                    <a class="bl-btn bl-btn-ondark" href="./Stocks" target="_self">Explore a stock</a>
                </div>
                <p class="bl-hero-meta">Free and open source (MIT). For learning, not investment advice.</p>
                <dl class="bl-band-stats">
                    <div><dt>2</dt><dd>optimization models</dd></div>
                    <div><dt>4</dt><dd>Markowitz objectives</dd></div>
                    <div><dt>{TEST_COUNT}</dt><dd>automated tests</dd></div>
                    <div><dt>6</dt><dd>MIT reference cases</dd></div>
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
                st.plotly_chart(
                    create_example_frontier_figure(data), theme=None, width="stretch",
                    config={"displayModeBar": False, "scrollZoom": False},
                )
                st.markdown(f"""
                <div class="bl-dark">
                    <ul class="bl-fig-legend" aria-hidden="true">
                        <li><i class="sw-line"></i>Efficient frontier</li>
                        <li><i class="sw-dash"></i>Capital market line</li>
                        <li><i class="sw-dot"></i>Max Sharpe</li>
                        <li><i class="sw-diamond"></i>Min variance</li>
                        <li><i class="sw-square"></i>Assets A–E</li>
                    </ul>
                    <p class="bl-fig-caption">Five example assets, {len(data["cloud"]):,} random long-only portfolios and a {_pct(data["rf"], 0)} risk-free rate, solved with PyPortfolioOpt. Hover over the chart to read any point.</p>
                </div>
                """, unsafe_allow_html=True)


def _tools(data: dict) -> None:
    """The two tool cards; their top picture is drawn from example data."""
    st.markdown("""
    <div class="bl-block-head">
        <p class="bl-eyebrow">The tools</p>
        <h2>Explore a market, then build a portfolio</h2>
        <p class="bl-block-lead">Two tools that share the same data and the same care. Start with one asset, or go straight to a full allocation.</p>
    </div>
    """, unsafe_allow_html=True)

    ms = data["max_sharpe"]
    order = sorted(range(len(data["names"])), key=lambda i: ms["weights"][i], reverse=True)
    weights_html = "".join(
        f'<div class="bl-w-row"><span>{data["names"][i]}</span>'
        f'<div class="bl-w-track"><div class="bl-w-fill" style="width:{ms["weights"][i] * 100:.1f}%;'
        f'background:{data["colors"][i]}"></div></div>'
        f'<span class="pct">{_pct(ms["weights"][i])}</span></div>'
        for i in order
    )

    # Links are relative for the same reason as the navbar's (utils/styles.py).
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(f"""
        <a href="./Stocks" target="_self" class="bl-tool-card bl-animate bl-animate-delay-1">
            <div class="bl-tool-visual" aria-hidden="true">
                <div class="bl-tool-visual-head">
                    <span>Example price series</span>
                    <span class="bl-chips"><span>1D</span><span>5D</span><span>1M</span><span class="on">6M</span><span>YTD</span><span>1Y</span><span>5Y</span><span>All</span></span>
                </div>
                <div class="bl-candles">{_example_candles_html()}</div>
            </div>
            <div class="bl-tool-body">
                <h3>Stocks</h3>
                <p>Charts, fundamentals and analyst views for any Yahoo Finance symbol, from stocks and ETFs to crypto and indices.</p>
                <ul class="bl-checks">
                    <li>Line and candlestick charts with volume, from intraday to the full history</li>
                    <li>Ten key metrics and fundamentals at a glance</li>
                    <li>Analyst consensus and price target</li>
                    <li>Trailing returns up to five years, compared with the S&amp;P 500</li>
                </ul>
                <span class="bl-tool-link">Open Stocks &rarr;</span>
            </div>
        </a>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <a href="./Portfolio" target="_self" class="bl-tool-card bl-animate bl-animate-delay-2">
            <div class="bl-tool-visual" aria-hidden="true">
                <div class="bl-tool-visual-head">
                    <span>Max Sharpe portfolio of Fig. 1</span>
                    <span>weights</span>
                </div>
                <div>
                    <div class="bl-weights">{weights_html}</div>
                    <div class="bl-metrics"><span>Return <b>{_pct(ms["ret"])}</b></span><span>Volatility <b>{_pct(ms["vol"])}</b></span><span>Sharpe <b>{ms["sharpe"]:.2f}</b></span></div>
                </div>
            </div>
            <div class="bl-tool-body">
                <h3>Portfolio</h3>
                <p>Optimize with Black-Litterman or Markowitz, then turn the weights into whole shares for your budget.</p>
                <ul class="bl-checks">
                    <li>Your own return views with a confidence range (Black-Litterman)</li>
                    <li>Four objectives, from minimum variance to a target return (Markowitz)</li>
                    <li>Efficient frontier, backtest and correlation charts</li>
                    <li>A PDF report of the full analysis</li>
                </ul>
                <span class="bl-tool-link">Open Portfolio &rarr;</span>
            </div>
        </a>
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


def _verification(data: dict) -> None:
    """Navy band: how the results are checked, with a parity schematic."""
    ms = data["max_sharpe"]
    order = sorted(range(len(data["names"])), key=lambda i: ms["weights"][i], reverse=True)
    segments = "".join(
        f'<span style="width:{ms["weights"][i] * 100:.2f}%;background:{data["colors"][i]}">'
        f'{data["names"][i] if ms["weights"][i] > 0.09 else ""}</span>'
        for i in order if ms["weights"][i] > 0.005
    )
    st.markdown(f"""
    <div class="bl-band bl-verify">
        <div class="bl-band-inner bl-dark bl-verify-grid">
            <div>
                <p class="bl-eyebrow">Verification</p>
                <h2>Checked against the reference on every change</h2>
                <p class="bl-lead">PortfolioLab follows the PyPortfolioOpt cookbook. An automated suite compares its results with the library's own, and a change that moves any number makes the suite fail.</p>
                <dl class="bl-facts-dark">
                    <div><dt>Identical to PyPortfolioOpt</dt><dd>Six optimization paths, Black-Litterman with views included, produce exactly the library's weights and metrics.</dd></div>
                    <div><dt>Frozen snapshots</dt><dd>Exact results are stored and compared on each run, so a dependency upgrade cannot shift them unnoticed.</dd></div>
                    <div><dt>MIT reference cases</dt><dd>Six scenarios from MIT course material, reproduced with real market data.</dd></div>
                    <div><dt>Tested on every push</dt><dd>{TEST_COUNT} automated tests run on Python 3.12 and 3.14 for every change.</dd></div>
                </dl>
            </div>
            <div class="bl-parity" aria-label="Schematic of the parity check">
                <div class="bl-parity-label"><span>Parity check</span><span>schematic</span></div>
                <div class="bl-parity-row">
                    <div class="bl-parity-label"><span>PortfolioLab engine</span><span>Max Sharpe weights</span></div>
                    <div class="bl-parity-bar">{segments}</div>
                </div>
                <div class="bl-parity-row">
                    <div class="bl-parity-label"><span>PyPortfolioOpt 1.5.6</span><span>Max Sharpe weights</span></div>
                    <div class="bl-parity-bar">{segments}</div>
                </div>
                <div class="bl-parity-eq">Same inputs, same weights, same metrics.</div>
                <div class="bl-parity-foot">
                    <div><b>6 / 6</b>paths match</div>
                    <div><b>{TEST_COUNT}</b>tests pass</div>
                    <div><b>2</b>Python versions</div>
                </div>
                <p class="bl-parity-note">The bars show the example portfolio of Fig. 1 to illustrate the check. The real suite runs on synthetic market data with a fixed seed.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Home page: the public front door of PortfolioLab."""
    data = _example_market()
    _hero(data)
    _tools(data)
    _how_it_works()
    _verification(data)

    # ── Render Footer ──
    from utils.styles import render_footer
    render_footer()


if __name__ == "__main__":
    main()
