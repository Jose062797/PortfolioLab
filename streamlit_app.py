"""
PortfolioLab - Multi-Tool Financial Platform
Home page: a compact hero band and the two tool cards
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

# Page configuration. Every page uses the brand favicon (the landing page's
# too); a plain string that is not an emoji would be taken as an image URL.
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


# Example weights for the Portfolio card: decorative, not an optimization
# result. The colors are the asset colors of the landing page (docs/index.html).
EXAMPLE_WEIGHTS = [
    ("A", 31.4, "#2E6FC7"),
    ("B", 24.8, "#5B93E0"),
    ("C", 19.6, "#10B981"),
    ("D", 14.2, "#8DB8F2"),
    ("E", 10.0, "#F59E0B"),
]


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


def main():
    """Home page: hero band plus the two tool cards."""

    # ── Hero band ──
    # Same headline and stats as the landing page (docs/index.html). The
    # numbers are claims about the project: keep them in sync with it.
    st.markdown("""
    <div class="bl-band">
        <div class="bl-band-inner bl-animate">
            <p class="bl-eyebrow">Portfolio optimization lab</p>
            <h1>Build optimal portfolios. <span class="accent">Verify every number.</span></h1>
            <p class="bl-lead">Black-Litterman and Markowitz optimization on live market data, with interactive charts and a PDF report. Results match PyPortfolioOpt, the reference library, to the last digit.</p>
            <dl class="bl-band-stats">
                <div><dt>2</dt><dd>optimization models</dd></div>
                <div><dt>4</dt><dd>Markowitz objectives</dd></div>
                <div><dt>108</dt><dd>automated tests</dd></div>
                <div><dt>6</dt><dd>MIT reference cases</dd></div>
            </dl>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tool cards ──
    # The top of each card is a small CSS picture of the tool, drawn from
    # example data (no images to download, nothing that looks like advice).
    # Links are relative for the same reason as the navbar's (utils/styles.py).
    weights_html = "".join(
        f'<div class="bl-w-row"><span>{name}</span>'
        f'<div class="bl-w-track"><div class="bl-w-fill" style="width:{weight}%;background:{color}"></div></div>'
        f'<span class="pct">{weight:.1f}%</span></div>'
        for name, weight, color in EXAMPLE_WEIGHTS
    )

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
                    <span>Example allocation</span>
                    <span>weights</span>
                </div>
                <div class="bl-weights">{weights_html}</div>
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

    # ── Render Footer ──
    from utils.styles import render_footer
    render_footer()


if __name__ == "__main__":
    main()
