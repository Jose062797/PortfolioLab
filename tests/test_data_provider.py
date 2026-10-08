"""Tests for core.data_provider (the Stocks page's data layer).

The tests of download_prices and parse_yfinance_prices went with them on
2026-10-08: nothing used those helpers any more (audit B8-01).
"""

from types import SimpleNamespace

import pandas as pd
import pytest

from core.data_provider import download_ohlcv, get_asset_info


class TestAssetInfoDividendYield:
    """Yahoo mixes units: `dividendYield` is a percent, the trailing yield a fraction.

    The Stocks page multiplies `dividend_yield` by 100, so it must always be a
    fraction. Before the fix MSFT showed a 79.00 % yield instead of 0.79 %.
    """

    @staticmethod
    def _asset_info(monkeypatch, info):
        class FakeTicker:
            def __init__(self, symbol):
                self.info = info
                self.fast_info = SimpleNamespace()
                self.analyst_price_targets = {}

        monkeypatch.setattr("yfinance.Ticker", FakeTicker)
        get_asset_info.clear()  # st.cache_data would return an earlier call
        return get_asset_info("TEST")

    def test_percent_dividend_yield_becomes_a_fraction(self, monkeypatch):
        # As Yahoo reported MSFT on 2026-09-26
        result = self._asset_info(monkeypatch, {
            "dividendYield": 0.79, "trailingAnnualDividendYield": 0.0073,
        })

        assert result["dividend_yield"] == pytest.approx(0.0079)

    def test_trailing_yield_fallback_stays_a_fraction(self, monkeypatch):
        result = self._asset_info(monkeypatch, {"trailingAnnualDividendYield": 0.0073})

        assert result["dividend_yield"] == pytest.approx(0.0073)


class TestOhlcvRetry:
    """Yahoo sometimes answers a shared cloud server with an empty frame.

    Seen in production on 2026-09-26: the first Stocks search failed with
    "No data downloaded" and the same search worked a moment later.
    """

    @staticmethod
    def _ohlcv():
        index = pd.date_range("2026-01-02", periods=3, freq="B")
        return pd.DataFrame({
            "Open": [1.0, 2.0, 3.0], "High": [1.5, 2.5, 3.5], "Low": [0.5, 1.5, 2.5],
            "Close": [1.2, 2.2, 3.2], "Volume": [100, 200, 300],
        }, index=index)

    @staticmethod
    def _patch_download(monkeypatch, answers):
        """Serve `answers` in order (the last one repeats); count the calls."""
        calls = []

        def fake_download(*args, **kwargs):
            calls.append(args)
            return answers[min(len(calls), len(answers)) - 1]

        monkeypatch.setattr("yfinance.download", fake_download)
        monkeypatch.setattr("time.sleep", lambda seconds: None)
        download_ohlcv.clear()  # st.cache_data would return an earlier call
        return calls

    def test_empty_first_answer_is_retried(self, monkeypatch):
        calls = self._patch_download(monkeypatch, [pd.DataFrame(), self._ohlcv()])

        result = download_ohlcv("TEST")

        assert len(calls) == 2
        assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert len(result) == 3

    def test_gives_up_after_three_empty_answers(self, monkeypatch):
        calls = self._patch_download(monkeypatch, [pd.DataFrame()])

        with pytest.raises(ValueError, match="No data downloaded"):
            download_ohlcv("TEST")
        assert len(calls) == 3
