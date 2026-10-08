"""
Smoke tests for the remaining Streamlit pages (AppTest, offline).

These do not exercise business logic — that is covered elsewhere. They catch
the failure mode unit tests structurally cannot see: a page that raises on
import or first render (a bad import, a removed Streamlit API, a typo in a
widget call) and greets the user with a traceback.

Every case here renders without touching the network: the Stocks page returns
early on its empty state and on rejected symbols, and Home/About are static.
"""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
HOME_PAGE = str(ROOT / "streamlit_app.py")
STOCKS_PAGE = str(ROOT / "pages" / "1_Stocks.py")
ABOUT_PAGE = str(ROOT / "pages" / "3_About.py")

PAGE_TIMEOUT = 120


@pytest.fixture(autouse=True)
def clear_streamlit_caches():
    """
    st.cache_data is process-global, not per-session: the Stocks page would
    otherwise carry cached data across AppTest instances (and across test
    runs within a session), making these tests order-dependent.
    """
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def render(page_path):
    at = AppTest.from_file(page_path, default_timeout=PAGE_TIMEOUT)
    at.run()
    return at


def joined(elements):
    return "\n".join(e.value for e in elements)


class TestHomePage:

    def test_renders_without_exception(self):
        at = render(HOME_PAGE)

        assert not at.exception

    def test_shows_both_tool_cards(self):
        """The Home page's first job is routing to the two tools."""
        at = render(HOME_PAGE)
        body = joined(at.markdown)

        assert "Stocks" in body
        assert "Portfolio" in body

    def test_shows_educational_disclaimer(self):
        """Required on every page — see CLAUDE.md permanent instruction #4."""
        at = render(HOME_PAGE)

        assert "not investment advice" in joined(at.markdown).lower()

    def test_hero_buttons_follow_the_tools_order(self):
        """Look an asset up first, then build the portfolio: the hero buttons go
        in the same order as the tool cards below them (the user's call,
        2026-09-27)."""
        at = render(HOME_PAGE)
        hero = next(m.value for m in at.markdown if 'class="bl-hero"' in m.value)
        body = joined(at.markdown)

        assert hero.index('href="./Stocks"') < hero.index('href="./Portfolio"')
        assert body.index("<h3>Stocks</h3>") < body.index("<h3>Portfolio</h3>")


class TestAboutPage:

    def test_renders_without_exception(self):
        at = render(ABOUT_PAGE)

        assert not at.exception

    def test_documents_both_models(self):
        """Model comparison lives in st.info/st.success inside the first tab."""
        at = render(ABOUT_PAGE)
        body = joined(at.markdown) + joined(at.info) + joined(at.success)

        assert "Black-Litterman" in body
        assert "Markowitz" in body


class TestAccessibility:
    """Audit 2026-10-08, package D. axe-core and a keyboard walk found these in
    the real app; the tests keep them from coming back."""

    def test_no_pwa_iframe_on_the_pages(self, monkeypatch):
        """The PWA helper was a 1x1 iframe: the first Tab stop on every page,
        announced as "st.iframe", for a worker that never controlled the app."""
        from utils import styles

        def _no_iframes(*args, **kwargs):
            raise AssertionError("inject_styles must not add an iframe")

        monkeypatch.setattr(styles.st, "iframe", _no_iframes)
        styles.inject_styles()

        assert not (ROOT / "static" / "sw.js").exists()
        assert not (ROOT / "static" / "manifest.json").exists()

    def test_focus_ring_is_solid_accent(self):
        """The 35%-alpha ring measured about 2:1 on white; a focus indicator
        needs 3:1, and the solid accent gives 4.99:1."""
        import re
        from utils.styles import get_shared_css

        css = get_shared_css()
        rule = re.search(r"a:focus-visible,[^{]*\{([^}]*)\}", css).group(1)

        assert "outline: 3px solid var(--color-accent) !important" in rule
        assert "accent-ring" not in css
        # Tab panels and Streamlit's main scroll area (the first Tab stop)
        # take focus too, and showed none before 2026-10-08
        assert '[role="tabpanel"]:focus-visible' in css
        main = re.search(r'section\[data-testid="stMain"\]:focus-visible \{([^}]*)\}', css).group(1)
        assert "solid var(--color-accent)" in main

    def test_headings_follow_the_outline(self):
        """h1 page title, h2 form steps and model cards, h3 sections inside
        them: no jump from h1 to h4 (axe "heading-order")."""
        about = render(ABOUT_PAGE)
        portfolio = render(str(ROOT / "pages" / "2_Portfolio.py"))
        about_md, portfolio_md = joined(about.markdown), joined(portfolio.markdown)

        assert 'role="heading" aria-level="2">Markowitz' in about_md
        assert 'role="heading" aria-level="2">Black-Litterman' in about_md
        assert 'role="heading" aria-level="2">Assets and budget' in portfolio_md
        assert not any(line.lstrip().startswith("#### ")
                       for line in (about_md + "\n" + portfolio_md).splitlines())

    def test_active_navbar_link_text_has_contrast(self):
        """The plain accent on the active tint measured 4.3:1 (text needs 4.5)."""
        import re
        from utils.styles import get_shared_css

        rule = re.search(r"\.bl-navbar-links a\.active \{([^}]*)\}", get_shared_css()).group(1)
        assert "color: var(--color-accent-hover)" in rule

    def test_captions_use_the_secondary_text_color(self):
        """Streamlit's caption grey measured 3.3:1 on the page background."""
        import re
        from utils.styles import get_shared_css

        css = get_shared_css()
        rule = re.search(r'\[data-testid="stCaptionContainer"\] p \{([^}]*)\}', css).group(1)
        assert "color: var(--color-text-secondary) !important" in rule
        container = re.search(r'\[data-testid="stCaptionContainer"\] \{([^}]*)\}', css).group(1)
        assert "opacity: 1 !important" in container, "Streamlit draws captions at 0.6"

    def test_footer_link_is_a_44px_target(self):
        import re
        from utils.styles import get_shared_css

        rule = re.search(r"\.bl-footer a \{([^}]*)\}", get_shared_css()).group(1)

        assert "min-height: 44px" in rule


class TestStocksPage:

    def test_empty_state_renders_without_network(self):
        at = render(STOCKS_PAGE)

        assert not at.exception
        assert "Search for any stock" in joined(at.markdown)

    def test_malformed_symbol_rejected_before_download(self, monkeypatch):
        """
        The allowlist must reject typos without a network round-trip. Any
        yfinance call here would be a regression (and would hang CI).
        """
        import yfinance

        def _explode(*args, **kwargs):
            raise AssertionError("network hit for a symbol the allowlist should reject")

        monkeypatch.setattr(yfinance, "download", _explode)

        at = render(STOCKS_PAGE)
        at.text_input[0].set_value("BAD!TICKER").run()
        at.button[0].click().run()

        assert not at.exception
        warnings = joined(at.warning)
        # Named in the warning, escaped so markdown shows it literally (B5-07)
        assert "BAD\\!TICKER" in warnings
        assert "not a valid ticker symbol" in warnings

    def test_multiple_symbols_rejected(self):
        at = render(STOCKS_PAGE)
        at.text_input[0].set_value("AAPL MSFT").run()
        at.button[0].click().run()

        assert not at.exception
        assert "one symbol at a time" in joined(at.warning)
