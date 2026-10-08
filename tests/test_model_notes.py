"""
Model decisions of 2026-10-08 and the notes and texts that explain results
(audit package F). Offline: synthetic prices and session-state toggles.
"""

import logging
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from fpdf import FPDF
from streamlit.testing.v1 import AppTest

from core.constants import CALENDAR_DAYS_PER_YEAR, TRADING_DAYS_PER_YEAR, risk_free_text

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PAGE = str(ROOT / "pages" / "2_Portfolio.py")
ABOUT_PAGE = str(ROOT / "pages" / "3_About.py")
PAGE_TIMEOUT = 180


def _crypto_market():
    """Two coins priced every day of the week, SPY on weekdays only."""
    rng = np.random.default_rng(7)
    days = pd.date_range("2023-01-01", periods=700, freq="D")
    coins = pd.DataFrame({
        "BTC-USD": 30000 * np.cumprod(1 + rng.normal(0.0012, 0.035, len(days))),
        "ETH-USD": 2000 * np.cumprod(1 + rng.normal(0.0010, 0.045, len(days))),
    }, index=days)
    weekdays = days[days.dayofweek < 5]
    spy = pd.Series(400 * np.cumprod(1 + rng.normal(0.0004, 0.01, len(weekdays))), index=weekdays)
    return coins, spy


def _patch_crypto_download(coins, spy):
    def _download(tickers, **kwargs):
        if tickers == "SPY" or tickers == ["SPY"]:
            return pd.DataFrame({"Close": spy})
        closes = coins[list(tickers)]
        closes.columns = pd.MultiIndex.from_product([["Close"], list(tickers)], names=["Price", "Ticker"])
        return closes
    return patch("yfinance.download", side_effect=_download)


class TestCalendarDays:

    def test_rows_per_year_follow_the_calendar(self):
        from utils.optimizer_wrapper import trading_days_per_year

        weekdays = pd.DataFrame({"A": 1.0}, index=pd.bdate_range("2024-01-01", periods=300))
        every_day = pd.DataFrame({"A": 1.0}, index=pd.date_range("2024-01-01", periods=300))

        assert trading_days_per_year(weekdays) == TRADING_DAYS_PER_YEAR
        assert trading_days_per_year(every_day) == CALENDAR_DAYS_PER_YEAR

    def test_all_crypto_equals_pypfopt_at_365_days(self):
        """The engine with frequency=365 is still PyPortfolioOpt called with
        it: weights and volatility match exactly (audit F1-02)."""
        from pypfopt import EfficientFrontier, expected_returns, risk_models
        from utils.optimizer_wrapper import run_optimization

        coins, spy = _crypto_market()
        with _patch_crypto_download(coins, spy), patch("time.sleep"):
            result = run_optimization(["BTC-USD", "ETH-USD"], 10000, model_type="Markowitz",
                                      obj_function="Min Variance", returns_estimator="historical")
        assert result["success"], result.get("error")
        assert result["trading_days_per_year"] == 365

        mu = expected_returns.mean_historical_return(coins, frequency=365)
        S = risk_models.CovarianceShrinkage(coins, frequency=365).ledoit_wolf()
        ef = EfficientFrontier(mu, S)
        ef.min_volatility()
        weights = ef.clean_weights()
        ret, vol, _ = ef.portfolio_performance(risk_free_rate=0.03)

        for t in coins.columns:
            assert result["weights"][t] == pytest.approx(weights[t], abs=1e-9)
        assert result["metrics"]["volatility"] == pytest.approx(vol, rel=1e-9)
        # Lowest risk ignores expected returns when choosing weights; the
        # reported return still shows the historical mean's annualization
        assert result["metrics"]["return"] == pytest.approx(ret, rel=1e-9)

        S252 = risk_models.CovarianceShrinkage(coins).ledoit_wolf()
        w = np.array([weights[t] for t in coins.columns])
        vol252 = float(np.sqrt(w @ S252.values @ w))
        assert vol / vol252 == pytest.approx(np.sqrt(365 / 252), rel=1e-9), \
            "252 understated an every-day portfolio's volatility by about 17%"

    def test_black_litterman_risk_model_uses_365_days_too(self):
        from unittest.mock import MagicMock
        from pypfopt import risk_models
        from utils.optimizer_wrapper import run_optimization

        coins, spy = _crypto_market()

        def _ticker(symbol):
            t = MagicMock()
            t.info = {"marketCap": {"BTC-USD": 1.2e12, "ETH-USD": 4e11}.get(symbol, 1e9)}
            return t

        with _patch_crypto_download(coins, spy), patch("yfinance.Ticker", side_effect=_ticker), \
                patch("time.sleep"):
            result = run_optimization(["BTC-USD", "ETH-USD"], 10000, model_type="Black-Litterman")
        assert result["success"], result.get("error")

        S365 = risk_models.CovarianceShrinkage(coins, frequency=365).ledoit_wolf()
        np.testing.assert_allclose(np.array(result["covariance_matrix"]),
                                   S365.loc[["BTC-USD", "ETH-USD"], ["BTC-USD", "ETH-USD"]].values,
                                   rtol=1e-12)


class TestDataNotes:

    def test_an_asset_whose_prices_end_early_is_noted(self):
        from utils.optimizer_wrapper import _data_notes

        index = pd.bdate_range("2024-01-01", periods=200)
        prices = pd.DataFrame({"A": 1.0, "B": 1.0}, index=index)
        prices.loc[index[150]:, "B"] = np.nan

        notes = _data_notes(prices)
        assert notes["early_end_assets"] == [("B", index[149].strftime("%Y-%m-%d"))]

    def test_shrinkage_grows_as_data_shrinks(self, synthetic_prices, mock_yfinance):
        from core.opt_engine import shrinkage_intensity
        from utils.optimizer_wrapper import run_optimization

        prices = synthetic_prices[["AAPL", "MSFT", "GOOGL"]]
        assert shrinkage_intensity(prices.head(30)) > shrinkage_intensity(prices)

        result = run_optimization(["AAPL", "MSFT", "GOOGL"], 10000, model_type="Markowitz")
        assert result["data_notes"]["shrinkage"] == pytest.approx(shrinkage_intensity(prices))
        assert result["data_notes"]["common_days"] == len(prices)


def _page_with_result(mock):
    at = AppTest.from_file(PORTFOLIO_PAGE, default_timeout=PAGE_TIMEOUT)
    at.run()
    at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
    next(b for b in at.button if b.label == "Run optimization").click().run()
    assert at.session_state["optimization_result"]["success"]
    return at


def _notes(at):
    boxes = [e for e in list(at.expander) + list(at.status)
             if e.label.startswith("Notes about these results")]
    return "\n".join([e.label for e in boxes] + ["\n".join(m.value for m in e.markdown) for e in boxes])


class TestNotesOnThePage:

    def test_notes_for_little_data_every_day_trading_and_early_ends(self, mock_yfinance_extended):
        at = _page_with_result(mock_yfinance_extended)
        assert "Little data" not in _notes(at), "500 days of data: no note"

        notes = at.session_state["optimization_result"]["data_notes"]
        notes.update(shrinkage=0.93, common_days=63, trading_days_per_year=365,
                     early_end_assets=[("GOOGL", "2023-06-30")])
        at.run()
        text = _notes(at)

        assert "Little data for the risk model" in text and "63 days" in text and "93%" in text
        assert "Every day a trading day" in text and "365 days a year" in text
        assert "GOOGL has none after 2023-06-30" in text

    def test_correlation_caption_names_the_starting_risk_model(self, mock_yfinance_extended):
        at = _page_with_result(mock_yfinance_extended)
        assert "the risk model both optimizers start from" in "\n".join(c.value for c in at.caption)

    def test_non_equity_warning_names_only_the_model_in_use(self):
        at = AppTest.from_file(PORTFOLIO_PAGE, default_timeout=PAGE_TIMEOUT)
        at.run()
        at.text_input("tickers_input").set_value("BTC-USD, ETH-USD").run()
        assert "CAPM measures" in "\n".join(w.value for w in at.warning)

        at.selectbox("returns_estimator_select").set_value("Historical mean").run()
        assert not [w for w in at.warning if "not stocks" in w.value], \
            "Markowitz on the historical mean: no model caveat left to give"

        at.selectbox("model_type_select").set_value("Black-Litterman").run()
        warnings = "\n".join(w.value for w in at.warning)
        assert "Black-Litterman starts from market values" in warnings and "CAPM" not in warnings


class TestTexts:

    def test_risk_free_rate_of_black_litterman_names_the_prior(self):
        assert risk_free_text({"model_type": "Markowitz", "risk_free_rate": 0.03}) == "3%"
        assert risk_free_text({"model_type": "Black-Litterman", "risk_free_rate": 0.03}) == \
            "3% (optimizer); 0% in the market-implied prior"

    def test_glossary_defines_the_figures_the_app_shows(self):
        at = AppTest.from_file(ABOUT_PAGE, default_timeout=PAGE_TIMEOUT)
        at.run()
        glossary = "\n".join(m.value for m in at.markdown)

        for term in ("Sortino ratio", "Calmar ratio", "Max drawdown", "Prior and posterior",
                     "Ledoit-Wolf shrinkage", "CAPM"):
            assert f"**{term}**" in glossary, term
        assert "averaged over every day" in glossary, "our Sortino-van der Meer convention"

    def test_the_server_log_does_not_get_the_budget(self, mock_yfinance, caplog):
        from utils.optimizer_wrapper import run_optimization

        with caplog.at_level(logging.INFO):
            run_optimization(["AAPL", "MSFT", "GOOGL"], 12345, model_type="Markowitz")

        assert not [r for r in caplog.records if "invested" in r.getMessage() or "remaining" in r.getMessage()]


class TestPdfNotes:

    def test_the_report_carries_the_data_notes_and_the_prior_rate(self, mock_yfinance, monkeypatch):
        from utils.optimizer_wrapper import run_optimization
        from utils.pdf_generator import generate_portfolio_pdf

        result = run_optimization(["AAPL", "MSFT", "GOOGL"], 10000, model_type="Markowitz")
        result["data_notes"].update(shrinkage=0.93, common_days=63, trading_days_per_year=365)
        result = dict(result, model_type="Black-Litterman")

        texts = []
        original = FPDF.multi_cell

        def multi_cell(self, *args, **kwargs):
            texts.append(str(args[2] if len(args) > 2 else kwargs.get("text", "")))
            return original(self, *args, **kwargs)

        monkeypatch.setattr(FPDF, "multi_cell", multi_cell)
        generate_portfolio_pdf(result)
        text = "\n".join(texts)

        assert "Little data for the risk model: with 63 days" in text
        assert "365 days a year" in text
        assert "3% (optimizer); 0% in the market-implied prior" in text
        assert "the risk aversion uses SPY's whole history" in text
