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
        """The landing page's whole job is routing to the two tools."""
        at = render(HOME_PAGE)
        body = joined(at.markdown)

        assert "Stocks" in body
        assert "Portfolio" in body

    def test_shows_educational_disclaimer(self):
        """Required on every page — see CLAUDE.md permanent instruction #4."""
        at = render(HOME_PAGE)

        assert "not investment advice" in joined(at.markdown).lower()


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
        assert "BAD!TICKER" in warnings
        assert "not a valid ticker symbol" in warnings

    def test_multiple_symbols_rejected(self):
        at = render(STOCKS_PAGE)
        at.text_input[0].set_value("AAPL MSFT").run()
        at.button[0].click().run()

        assert not at.exception
        assert "one symbol at a time" in joined(at.warning)
