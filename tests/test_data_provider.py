"""Tests for core.data_provider — yfinance parsing logic."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from core.data_provider import parse_yfinance_prices, download_prices, download_ohlcv, get_asset_info


class TestParseYfinancePrices:
    """Test the yfinance output parser for various data shapes."""

    def test_single_ticker_flat_columns(self):
        """Single ticker → flat columns with 'Close'."""
        dates = pd.bdate_range("2023-01-02", periods=10)
        raw = pd.DataFrame({
            "Open": np.random.rand(10) * 100,
            "High": np.random.rand(10) * 100,
            "Low": np.random.rand(10) * 100,
            "Close": np.arange(100, 110, dtype=float),
            "Volume": np.random.randint(1e6, 1e7, 10),
        }, index=dates)

        result = parse_yfinance_prices(raw, ["AAPL"])

        assert list(result.columns) == ["AAPL"]
        assert len(result) == 10
        assert result["AAPL"].iloc[0] == 100.0

    def test_multi_ticker_multiindex(self):
        """Multi ticker → MultiIndex columns with ('Close', 'AAPL') etc."""
        dates = pd.bdate_range("2023-01-02", periods=10)
        tickers = ["AAPL", "MSFT"]

        tuples = []
        data = {}
        for price_type in ["Close", "Volume"]:
            for ticker in tickers:
                key = (price_type, ticker)
                tuples.append(key)
                if price_type == "Close":
                    data[key] = np.arange(100, 110, dtype=float)
                else:
                    data[key] = np.random.randint(1e6, 1e7, 10)

        idx = pd.MultiIndex.from_tuples(tuples, names=["Price", "Ticker"])
        raw = pd.DataFrame(data, index=dates)
        raw.columns = idx

        result = parse_yfinance_prices(raw, tickers)

        assert set(result.columns) == {"AAPL", "MSFT"}
        assert len(result) == 10

    def test_empty_dataframe_raises(self):
        """Empty input should raise ValueError."""
        with pytest.raises(ValueError, match="Empty DataFrame"):
            parse_yfinance_prices(pd.DataFrame(), ["AAPL"])

    def test_nan_rows_dropped(self):
        """Rows with NaN should be dropped."""
        dates = pd.bdate_range("2023-01-02", periods=5)
        raw = pd.DataFrame({
            "Close": [100.0, np.nan, 102.0, 103.0, 104.0],
        }, index=dates)

        result = parse_yfinance_prices(raw, ["AAPL"])
        assert len(result) == 4
        assert result["AAPL"].isna().sum() == 0


class TestDownloadPrices:
    """Test download_prices with mocked yfinance."""

    def test_download_with_mock(self, mock_yfinance, portfolio_tickers):
        """download_prices should return clean DataFrame using mock data."""
        result = download_prices(
            portfolio_tickers,
            start="2022-01-03",
            end="2023-06-01",
        )

        assert isinstance(result, pd.DataFrame)
        for t in portfolio_tickers:
            assert t in result.columns
        assert len(result) > 0
        assert result.isna().sum().sum() == 0


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
