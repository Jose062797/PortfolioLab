"""
Third-party and typed text stays text (audit 2026-10-08, package E).

Yahoo's fields (names, sectors, currencies, figures that arrive as strings)
and whatever a visitor types must never become HTML or markdown on the page,
and an odd value must show as N/A instead of crashing it. Also guards the
security settings in .streamlit/config.toml and utils/ssl_fix.

All offline: the Stocks page's data functions are replaced by fakes.
"""

import os
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
STOCKS_PAGE = str(ROOT / "pages" / "1_Stocks.py")
PORTFOLIO_PAGE = str(ROOT / "pages" / "2_Portfolio.py")
PAGE_TIMEOUT = 120


@pytest.fixture(autouse=True)
def clear_streamlit_caches():
    """st.cache_data is process-global: keep fake data from leaking between tests."""
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def _ohlcv(days=300):
    index = pd.bdate_range(end="2026-10-07", periods=days)
    close = pd.Series(np.linspace(100.0, 130.0, days), index=index)
    return pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1,
                         "Close": close, "Volume": 1_000_000.0})


def _stocks_page_with(monkeypatch, info):
    """The Stocks page after searching for FAKE, with `info` as Yahoo's answer."""
    import core.data_provider as dp

    monkeypatch.setattr(dp, "download_ohlcv", lambda ticker, **kw: _ohlcv())
    monkeypatch.setattr(dp, "get_asset_info", lambda ticker: dict(info))
    monkeypatch.setattr(dp, "get_quarterly_financials", lambda ticker: pd.DataFrame())

    at = AppTest.from_file(STOCKS_PAGE, default_timeout=PAGE_TIMEOUT)
    at.run()
    at.text_input[0].set_value("FAKE").run()
    at.button[0].click().run()
    return at


def _markdown(at):
    return "\n".join(m.value for m in at.markdown)


def _header(at):
    """The price header: name, tag, price and currency."""
    return next(m.value for m in at.markdown if "font-size:2.2rem" in m.value)


class TestYahooTextOnTheStocksPage:

    def test_names_sectors_and_currency_are_escaped(self, monkeypatch):
        at = _stocks_page_with(monkeypatch, {
            "type": "EQUITY",
            "name": '<img src=x onerror="alert(1)">',
            "sector": "<b>Tech</b>",
            "industry": "Cars & <i>Trucks</i>",
            "currency": "<script>",
            "price": 130.0,
            "previous_close": 129.0,
        })
        assert not at.exception
        header = _header(at)

        assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in header
        assert "&lt;b&gt;Tech&lt;/b&gt;" in header
        assert "Cars &amp; &lt;i&gt;Trucks&lt;/i&gt;" in header
        assert "<img" not in header and "<b>Tech" not in header
        assert "script" not in header, "a currency that is not a 3-letter code is not shown"

    def test_a_real_currency_code_is_shown(self, monkeypatch):
        at = _stocks_page_with(monkeypatch, {
            "type": "EQUITY", "name": "Fake Co", "currency": "GBp",
            "price": 130.0, "previous_close": 129.0,
        })

        assert ">GBp</span>" in _header(at)

    def test_figures_that_arrive_as_text_show_as_na(self, monkeypatch):
        """trailingPE can come back as the string 'Infinity'; before 2026-10-08
        _fmt_safe printed it raw, and _fmt_number crashed on abs()."""
        at = _stocks_page_with(monkeypatch, {
            "type": "EQUITY", "name": "Fake Co",
            "price": 130.0, "previous_close": "n/a",
            "pe_ratio": "Infinity", "volume": "lots", "bid": "abc", "bid_size": 5,
            "dividend_rate": "x", "dividend_yield": 0.01, "market_cap": float("nan"),
            "beta": "<b>1.2</b>", "open_price": 128.5,
        })
        body = _markdown(at)

        assert not at.exception
        assert "Infinity" not in body and "lots" not in body and "abc" not in body
        assert "&lt;b&gt;" not in body and "<b>1.2" not in body
        assert "128.50" in body, "valid figures are still shown"


class TestTypedTextOnThePortfolioPage:

    def test_invalid_symbols_are_listed_escaped_and_block_run(self):
        at = AppTest.from_file(PORTFOLIO_PAGE, default_timeout=PAGE_TIMEOUT)
        at.run()
        at.text_input("tickers_input").set_value("AAPL, ![x](http://evil.test/i.png), MSFT").run()

        warnings = "\n".join(w.value for w in at.warning)
        run = next(b for b in at.button if b.label == "Run optimization")

        assert not at.exception
        assert "Not a valid ticker symbol" in warnings
        assert "\\!\\[X\\]\\(HTTP://EVIL\\.TEST/I\\.PNG\\)" in warnings
        assert run.disabled is True


class TestEscapeMarkdown:

    def test_markdown_syntax_becomes_literal(self):
        from utils.text import escape_markdown

        assert escape_markdown("**bold** [a](b) $x$ <i>") == \
            "\\*\\*bold\\*\\* \\[a\\]\\(b\\) \\$x\\$ \\<i\\>"
        assert escape_markdown("AAPL") == "AAPL"


class TestSecuritySettings:

    def test_config_hides_tracebacks_and_keeps_cors(self):
        config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))

        assert config["client"]["showErrorDetails"] in ("type", "none")
        assert config["server"].get("enableCORS", True) is True, \
            "Streamlit 1.59 only warns about enableCORS=false; it then allows every origin"
        assert config["server"]["enableXsrfProtection"] is True

    def test_urllib3_is_pinned_past_its_advisories(self):
        lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        pin = next(line for line in lines if line.startswith("urllib3=="))
        version = tuple(int(p) for p in pin.split("==")[1].split("."))

        assert version >= (2, 8, 0)


class TestSslFix:

    @pytest.fixture
    def env(self, monkeypatch, tmp_path):
        import certifi
        import utils.ssl_fix as ssl_fix

        monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

        def use_bundle(folder_name, content=b"certs v1"):
            bundle = tmp_path / folder_name / "cacert.pem"
            bundle.parent.mkdir(parents=True, exist_ok=True)
            bundle.write_bytes(content)
            monkeypatch.setattr(certifi, "where", lambda: str(bundle))
            return bundle

        return ssl_fix, use_bundle, tmp_path / "local" / "ssl" / "cacert.pem"

    def test_does_nothing_on_an_ascii_path(self, env):
        ssl_fix, use_bundle, copy = env
        use_bundle("plain")
        ssl_fix.apply_ssl_fix()

        assert "CURL_CA_BUNDLE" not in os.environ
        assert not copy.exists()

    def test_copies_and_refreshes_on_a_non_ascii_path(self, env):
        ssl_fix, use_bundle, copy = env
        use_bundle("Católica")
        ssl_fix.apply_ssl_fix()

        assert os.environ["CURL_CA_BUNDLE"] == str(copy)
        assert copy.read_bytes() == b"certs v1"

        use_bundle("Católica", b"certs v2")  # certifi upgraded
        ssl_fix.apply_ssl_fix()

        assert copy.read_bytes() == b"certs v2"
