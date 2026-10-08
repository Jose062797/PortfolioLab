"""
Stocks page with a symbol on screen (AppTest, offline).

The page's data functions are replaced by fakes before the run, so these
tests reach the rendering path a real search takes: header, chart, returns
strip and the tabs of each asset type. Until 2026-10-08 only the empty state
and rejected symbols were tested, and the page sat at 16 % line coverage
(audit B7-01); the audit's Stocks fixes (package C) are pinned here too.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from utils.text import fmt_price

STOCKS_PAGE = str(Path(__file__).resolve().parents[1] / "pages" / "1_Stocks.py")
PAGE_TIMEOUT = 120


@pytest.fixture(autouse=True)
def clear_streamlit_caches():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def _daily(days=1300, start=100.0, end=130.0):
    index = pd.bdate_range(end="2026-10-07", periods=days)
    close = pd.Series(np.linspace(start, end, days), index=index)
    return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99,
                         "Close": close, "Volume": 1_000_000.0})


def _five_minute_bars(sessions=7):
    """5-minute bars over `sessions` weekdays, as Yahoo's 5D download returns."""
    days = pd.bdate_range(end="2026-10-07", periods=sessions)
    index = pd.DatetimeIndex([d + pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(minutes=5 * i)
                              for d in days for i in range(78)])
    close = pd.Series(np.linspace(100.0, 110.0, len(index)), index=index)
    return pd.DataFrame({"Open": close, "High": close + 0.1, "Low": close - 0.1,
                         "Close": close, "Volume": 10_000.0})


def _stocks(monkeypatch, info, download=None, financials=None):
    import core.data_provider as dp

    def _default_download(ticker, **kw):
        return _five_minute_bars() if kw.get("interval") == "5m" else _daily()

    monkeypatch.setattr(dp, "download_ohlcv", download or _default_download)
    monkeypatch.setattr(dp, "get_asset_info", lambda ticker: dict(info))
    monkeypatch.setattr(dp, "get_quarterly_financials", financials or (lambda ticker: pd.DataFrame()))

    at = AppTest.from_file(STOCKS_PAGE, default_timeout=PAGE_TIMEOUT)
    at.run()
    at.text_input[0].set_value("FAKE").run()
    at.button[0].click().run()
    return at


def _markdown(at):
    return "\n".join(m.value for m in at.markdown)


def _tab_labels(at):
    return [t.label for t in at.tabs]


EQUITY = {"type": "EQUITY", "name": "Fake Co", "sector": "Technology", "price": 130.0,
          "previous_close": 129.0, "currency": "USD"}


class TestFmtPrice:

    @pytest.mark.parametrize("value, shown", [
        (1234.5, "1,234.50"), (1.0, "1.00"), (0.0, "0.00"),
        (0.05, "0.05000"), (0.00001234, "0.00001234"), (-0.0025, "-0.002500"),
    ])
    def test_two_decimals_or_four_significant_digits(self, value, shown):
        assert fmt_price(value) == shown


class TestAssetTypes:
    """Each asset type gets its own tabs; all render without an exception."""

    def test_stock(self, monkeypatch):
        at = _stocks(monkeypatch, EQUITY)
        assert not at.exception
        assert _tab_labels(at) == ["Key statistics", "Performance", "Revenue and earnings"]

    def test_etf(self, monkeypatch):
        at = _stocks(monkeypatch, {"type": "ETF", "name": "Fake Fund", "price": 50.0,
                                   "previous_close": 49.0, "fund_family": "Fake Funds",
                                   "net_assets": 2e9, "expense_ratio": 0.0003})
        assert not at.exception
        assert _tab_labels(at) == ["Market data", "Fund details"]
        assert "Fake Funds" in _markdown(at)

    def test_crypto(self, monkeypatch):
        at = _stocks(monkeypatch, {"type": "CRYPTOCURRENCY", "name": "Fake Coin", "price": 2.0,
                                   "previous_close": 1.9, "circulating_supply": 1e9})
        assert not at.exception
        assert _tab_labels(at) == ["Market and supply"]

    def test_index_has_no_currency(self, monkeypatch):
        at = _stocks(monkeypatch, {"type": "INDEX", "name": "Fake Index", "price": 5000.0,
                                   "previous_close": 4990.0, "currency": "USD"})
        assert not at.exception
        assert _tab_labels(at) == ["Market data"]
        header = next(m.value for m in at.markdown if "font-size:2.2rem" in m.value)
        assert "USD" not in header, "index levels are points"


class TestReturnsStrip:

    def test_is_a_grid_without_a_hidden_scroll(self, monkeypatch):
        """It used to scroll sideways with its scrollbar hidden: on phones 5Y
        and All were off screen and the keyboard could not reach them."""
        at = _stocks(monkeypatch, EQUITY)
        strip = next(m.value for m in at.markdown if m.value.startswith('<div class="bl-returns">'))

        assert "overflow-x" not in strip and "scrollbar-width" not in strip
        assert strip.count("bl-returns-label") == 8

    def test_huge_returns_fit_the_cell(self, monkeypatch):
        """+265132.05% broke in two on a 375 px phone."""
        at = _stocks(monkeypatch, EQUITY,
                     download=lambda ticker, **kw: _daily(start=0.05, end=130.0))
        strip = next(m.value for m in at.markdown if m.value.startswith('<div class="bl-returns">'))

        assert "+259,900%" in strip  # All: 130 / 0.05 - 1

    def test_closes_of_zero_are_not_a_base(self, monkeypatch):
        """Yahoo starts SHIB-USD with 217 closes of 0; the All return was +inf%."""
        def _download(ticker, **kw):
            data = _daily(start=1.0, end=2.0)
            data.iloc[:50, :4] = 0.0
            return data

        at = _stocks(monkeypatch, dict(EQUITY, price=2.0, previous_close=1.99), download=_download)
        strip = next(m.value for m in at.markdown if m.value.startswith('<div class="bl-returns">'))
        first_real_close = np.linspace(1.0, 2.0, 1300)[50]

        assert "inf" not in strip
        assert f"{2.0 / first_real_close - 1:+.2%}" in strip  # All, from the first close above 0

    def test_grid_wraps_to_two_rows_on_phones(self):
        import re
        from utils.styles import get_shared_css

        css = get_shared_css()
        phone = re.search(r"@media \(max-width: 640px\) \{\s*\.bl-returns \{([^}]*)\}", css).group(1)
        assert "repeat(4, minmax(0, 1fr))" in phone


class TestFiveDayChart:

    def test_shows_the_last_five_sessions(self, monkeypatch):
        """Starting five calendar days back gave four sessions on most days;
        the strip's 5D covers five (audit F1-04)."""
        at = _stocks(monkeypatch, EQUITY)
        at.radio[0].set_value("5D").run()

        spec = json.loads(at.get("plotly_chart")[0].proto.spec)
        days = {point[0].split(" ")[0] for point in spec["data"][0]["customdata"]}
        assert not at.exception
        assert len(days) == 5


class TestContrast:

    def test_gains_use_a_green_dark_enough_for_text(self, monkeypatch):
        """#16A34A measured 3.1:1 on the page background (axe); #15803D is 4.8."""
        at = _stocks(monkeypatch, EQUITY)
        header = next(m.value for m in at.markdown if "font-size:2.2rem" in m.value)
        strip = next(m.value for m in at.markdown if m.value.startswith('<div class="bl-returns">'))

        assert "color:#15803D" in header and "color:#15803D" in strip
        assert "#16A34A" not in header + strip


class TestFormats:

    def test_a_price_under_a_cent_keeps_its_digits(self, monkeypatch):
        at = _stocks(monkeypatch, {"type": "CRYPTOCURRENCY", "name": "Tiny Coin",
                                   "price": 0.00001234, "previous_close": 0.00001200},
                     download=lambda ticker, **kw: _daily(start=0.00001, end=0.00002))
        header = next(m.value for m in at.markdown if "font-size:2.2rem" in m.value)

        assert ">0.00001234<" in header
        assert "+0.00000034" in header, "the change too"

    def test_volumes_are_whole_numbers(self, monkeypatch):
        at = _stocks(monkeypatch, dict(EQUITY, volume=523456, avg_volume=2_500_000))
        body = _markdown(at)

        assert "523,456<" in body and "523,456.00" not in body
        assert "2.50M" in body

    def test_trailing_yield_is_not_labelled_forward(self, monkeypatch):
        at = _stocks(monkeypatch, dict(EQUITY, dividend_rate=1.0, dividend_yield=0.0073,
                                       dividend_yield_trailing=True))
        body = _markdown(at)

        assert "Dividend &amp; Trailing Yield" in body or "Dividend & Trailing Yield" in body
        assert "Forward Dividend" not in body
