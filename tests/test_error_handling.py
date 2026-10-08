"""
What the user sees when something fails (audit 2026-10-08, package A).

Each test pins one fix: a failure must give a clear message in the form's own
terms, never stale results, raw exceptions or data from another period, and
it must reach the log. All offline (conftest's yfinance mocks or fakes).
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from core.constants import DataDownloadError, OptimizationError

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PAGE = str(ROOT / "pages" / "2_Portfolio.py")
STOCKS_PAGE = str(ROOT / "pages" / "1_Stocks.py")
PAGE_TIMEOUT = 180


@pytest.fixture(autouse=True)
def clear_streamlit_caches():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def joined(elements):
    return "\n".join(e.value for e in elements)


def run_button(at):
    return next(b for b in at.button if b.label == "Run optimization")


@pytest.fixture
def markowitz_inputs(synthetic_prices):
    from core.opt_engine import calculate_markowitz_inputs
    prices = synthetic_prices[["AAPL", "MSFT", "GOOGL"]]
    return calculate_markowitz_inputs(prices, returns_estimator="historical")


# ═══════════════════════════════════════════════════════════════════
# Engine: failures in the form's terms
# ═══════════════════════════════════════════════════════════════════

class TestOptimizationMessages:

    def test_risk_limit_below_the_lowest_risk_is_explained_in_percent(self, markowitz_inputs):
        from core.opt_engine import optimize_portfolio
        mu, S = markowitz_inputs

        with pytest.raises(OptimizationError) as exc:
            optimize_portfolio(mu, S, obj_function="Maximise Return for a Given Risk",
                               target_volatility=0.01)
        message = str(exc.value)

        assert message.startswith("The risk limit of 1% is below the lowest risk these assets allow (")
        assert "target_volatility" not in message, "PyPortfolioOpt's parameter name, not the form's"

    def test_target_return_above_the_highest_names_the_highest(self, markowitz_inputs):
        from core.opt_engine import optimize_portfolio
        mu, S = markowitz_inputs

        with pytest.raises(OptimizationError) as exc:
            optimize_portfolio(mu, S, obj_function="Minimise Risk for a Given Return",
                               target_return=5.0)

        assert str(exc.value).startswith(
            f"The target return of 500% is above the highest expected return of these "
            f"assets ({mu.max() * 100:.1f}%)")

    def test_solver_failure_is_not_a_python_tuple(self, markowitz_inputs, monkeypatch):
        from pypfopt import EfficientFrontier
        from pypfopt.exceptions import OptimizationError as SolverError
        from core.opt_engine import optimize_portfolio
        mu, S = markowitz_inputs

        def _fail(self, *a, **k):
            raise SolverError("Solver status: infeasible")

        monkeypatch.setattr(EfficientFrontier, "min_volatility", _fail)
        with pytest.raises(OptimizationError) as exc:
            optimize_portfolio(mu, S, obj_function="Min Variance")

        assert str(exc.value).startswith("The optimizer found no portfolio that meets this goal "
                                         "(Solver status: infeasible)")
        assert "('Please" not in str(exc.value)

    def test_unknown_objective_raises_instead_of_max_sharpe_at_zero(self, markowitz_inputs):
        from core.opt_engine import optimize_portfolio
        mu, S = markowitz_inputs

        with pytest.raises(OptimizationError, match="Unknown objective"):
            optimize_portfolio(mu, S, obj_function="Max Sharpee")

    def test_frontier_is_kept_when_no_tangency_portfolio_exists(self, markowitz_inputs):
        """No asset above the 3% risk-free rate: max_sharpe is impossible, the
        curve and the Min Variance point are not."""
        from core.opt_engine import calculate_efficient_frontier
        mu, S = markowitz_inputs
        low_mu = pd.Series(np.linspace(0.005, 0.02, len(mu)), index=mu.index)

        ef = calculate_efficient_frontier(low_mu, S, points=10)

        assert ef is not None and ef["mus"]
        assert ef["optimal_ret"] is None and ef["min_vol_risk"] > 0


class TestDownloadMessages:

    def test_benchmark_failure_is_a_download_error_that_clears_the_inputs(self, monkeypatch, synthetic_prices):
        import core.opt_engine as engine

        def _download(tickers, **kwargs):
            if tickers == "SPY":
                return pd.DataFrame()
            closes = synthetic_prices[tickers]
            closes.columns = pd.MultiIndex.from_product([["Close"], tickers], names=["Price", "Ticker"])
            return closes

        monkeypatch.setattr(engine, "_get_yf", lambda: type("yf", (), {"download": staticmethod(_download)}))
        monkeypatch.setattr("time.sleep", lambda s: None)

        with pytest.raises(DataDownloadError, match="Could not download SPY, the market benchmark") as exc:
            engine.download_data(["AAPL", "MSFT"], None)
        assert "Your tickers are fine" in str(exc.value)


# ═══════════════════════════════════════════════════════════════════
# Wrapper: domain errors keep their message, bugs do not leak
# ═══════════════════════════════════════════════════════════════════

class TestWrapperErrors:

    def test_unexpected_error_is_logged_with_traceback_and_not_shown_raw(self, mock_yfinance, monkeypatch, caplog):
        import utils.optimizer_wrapper as wrapper

        def _bug(*a, **k):
            raise KeyError("SPY")

        monkeypatch.setattr(wrapper, "calculate_markowitz_inputs", _bug)
        with caplog.at_level(logging.ERROR, logger="utils.optimizer_wrapper"):
            result = wrapper.run_optimization(["AAPL", "MSFT", "GOOGL"], 10000, model_type="Markowitz",
                                              obj_function="Min Variance")

        assert result["success"] is False and result["error_type"] == "unexpected"
        assert "'SPY'" not in result["error"]
        assert any(r.exc_info for r in caplog.records), "the traceback must reach the log"

    def test_domain_error_keeps_its_message_and_type(self, mock_yfinance):
        from utils.optimizer_wrapper import run_optimization

        result = run_optimization(["AAPL", "MSFT", "GOOGL"], 10000, model_type="Markowitz",
                                  obj_function="Maximise Return for a Given Risk",
                                  target_volatility=0.01)

        assert result["error_type"] == "OptimizationError"
        assert result["error"].startswith("The risk limit of 1%")


# ═══════════════════════════════════════════════════════════════════
# Portfolio page
# ═══════════════════════════════════════════════════════════════════

def _portfolio():
    at = AppTest.from_file(PORTFOLIO_PAGE, default_timeout=PAGE_TIMEOUT)
    at.run()
    return at


class TestPortfolioPage:

    def test_a_failed_run_does_not_leave_the_previous_result(self, mock_yfinance_extended):
        at = _portfolio()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
        run_button(at).click().run()
        assert at.metric, "the first run succeeds"

        at.selectbox("obj_function_select").set_value("Maximise Return for a Given Risk").run()
        at.number_input("target_volatility_pct").set_value(1.0).run()
        run_button(at).click().run()

        assert "No portfolio meets the goal" in joined(at.error)
        assert "The risk limit of 1% is below the lowest risk" in joined(at.error)
        assert not at.metric, "the old figures read as the answer to the new inputs"

    def test_inverted_dates_block_run(self, mock_yfinance_extended):
        import datetime as dt
        at = _portfolio()
        at.text_input("tickers_input").set_value("AAPL, MSFT").run()
        at.checkbox("use_date_range_checkbox").check().run()
        at.date_input[0].set_value(dt.date(2024, 6, 1)).run()
        at.date_input[1].set_value(dt.date(2024, 1, 1)).run()

        assert "start date must be before the end date" in joined(at.error)
        assert run_button(at).disabled is True

    def test_a_view_with_low_above_high_blocks_run(self, mock_yfinance_extended):
        at = _portfolio()
        at.selectbox("model_type_select").set_value("Black-Litterman").run()
        at.text_input("tickers_input").set_value("AAPL, MSFT").run()
        at.checkbox("add_views_checkbox").check().run()
        at.multiselect("selected_views_ms").set_value(["AAPL"]).run()
        at.number_input("low_AAPL").set_value(30.0).run()

        assert "Low must be below High" in joined(at.error)
        assert run_button(at).disabled is True

    def test_tickers_separated_by_spaces_and_typed_twice(self):
        at = _portfolio()
        at.text_input("tickers_input").set_value("aapl msft;GOOGL, AAPL").run()

        assert "at least 2" not in joined(at.warning)
        assert "AAPL is listed more than once; it counts once." in joined(at.caption)
        assert run_button(at).disabled is False

    def test_a_budget_below_every_share_price_is_explained(self, mock_yfinance_extended):
        """The cheapest synthetic asset ends at $173.81 (AAPL); $100 buys nothing."""
        at = _portfolio()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
        at.number_input("portfolio_value").set_value(100).run()
        run_button(at).click().run()

        assert at.session_state["optimization_result"]["success"]
        assert "does not buy a single whole share" in joined(at.caption)

    def test_example_link_sets_the_target_without_a_widget_warning(self, monkeypatch):
        """A Home example sets target_volatility_pct; with value= on the widget
        too, Streamlit logged a session-state conflict on every such visit."""
        from streamlit.elements.lib import policies
        warnings = []
        monkeypatch.setattr(policies._LOGGER, "warning", lambda msg, *a, **k: warnings.append(str(msg)))

        at = AppTest.from_file(PORTFOLIO_PAGE, default_timeout=PAGE_TIMEOUT)
        at.query_params["example"] = "stocks-bonds-gold"
        at.run()

        assert at.number_input("target_volatility_pct").value == 10.0
        assert not [w for w in warnings if "Session State API" in w]


# ═══════════════════════════════════════════════════════════════════
# Stocks page
# ═══════════════════════════════════════════════════════════════════

def _ohlcv(days=300):
    index = pd.bdate_range(end="2026-10-07", periods=days)
    close = pd.Series(np.linspace(100.0, 130.0, days), index=index)
    return pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1,
                         "Close": close, "Volume": 1_000_000.0})


INFO = {"type": "EQUITY", "name": "Fake Co", "price": 130.0, "previous_close": 129.0,
        "currency": "USD"}


def _stocks(monkeypatch, download=None, info=None, financials=None):
    import core.data_provider as dp

    monkeypatch.setattr(dp, "download_ohlcv", download or (lambda ticker, **kw: _ohlcv()))
    monkeypatch.setattr(dp, "get_asset_info", info or (lambda ticker: dict(INFO)))
    monkeypatch.setattr(dp, "get_quarterly_financials", financials or (lambda ticker: pd.DataFrame()))

    at = AppTest.from_file(STOCKS_PAGE, default_timeout=PAGE_TIMEOUT)
    at.run()
    at.text_input[0].set_value("FAKE").run()
    at.button[0].click().run()
    return at


def _raise(*a, **k):
    raise ValueError("Yahoo said no")


class TestStocksPage:

    def test_a_failed_period_download_is_said_not_drawn_with_1y_data(self, monkeypatch):
        def _download(ticker, **kw):
            if kw.get("interval") == "1d" and kw.get("period") in ("1y", "max"):
                return _ohlcv()
            raise ValueError("rate limited")

        at = _stocks(monkeypatch, download=_download)
        charts_before = len(at.get("plotly_chart"))
        at.radio[0].set_value("All").run()

        assert not at.exception
        assert "The All chart could not be loaded" in joined(at.warning)
        assert len(at.get("plotly_chart")) == charts_before - 1, "no chart of the wrong period"

    def test_no_prices_names_both_causes(self, monkeypatch):
        at = _stocks(monkeypatch, download=_raise)

        assert "No prices for FAKE" in joined(at.error)
        assert "Yahoo said no" not in joined(at.error), "no raw exception text"

    def test_missing_details_keep_the_page_and_say_so(self, monkeypatch):
        at = _stocks(monkeypatch, info=_raise)

        assert not at.exception
        assert "did not send this asset's details" in joined(at.info)
        assert at.get("plotly_chart"), "the prices still draw the chart"

    def test_failed_financials_are_not_reported_as_missing(self, monkeypatch):
        at = _stocks(monkeypatch, financials=_raise)
        assert "did not send the quarterly results" in joined(at.info)

        at = _stocks(monkeypatch)
        assert "has no quarterly results for this asset" in joined(at.info)


class TestDataProvider:

    def test_asset_info_raises_when_yahoo_sends_nothing(self, monkeypatch):
        """Raising keeps the failure out of st.cache_data, so a revisit retries."""
        from types import SimpleNamespace
        from core.data_provider import get_asset_info

        class EmptyTicker:
            def __init__(self, symbol):
                self.fast_info = SimpleNamespace()
                self.analyst_price_targets = {}

            @property
            def info(self):
                raise RuntimeError("429 Too Many Requests")

        monkeypatch.setattr("yfinance.Ticker", EmptyTicker)
        with pytest.raises(ValueError, match="sent no details"):
            get_asset_info("NOPE")


class TestBacktestChart:

    def test_missing_benchmark_is_an_error_not_a_silent_download(self, monkeypatch, synthetic_prices):
        import yfinance
        from utils.visualizations import create_historical_performance_chart

        downloads = []
        # Recorded, not raised: the chart's own except would swallow an error
        monkeypatch.setattr(yfinance, "download", lambda *a, **k: downloads.append(a) or pd.DataFrame())
        prices = synthetic_prices[["AAPL", "MSFT"]]  # no SPY
        fig, result = create_historical_performance_chart(
            {"AAPL": 0.5, "MSFT": 0.5}, ["AAPL", "MSFT"], 10000, prices_data=prices)

        assert downloads == [], "the web backtest must not download other data"
        assert result is None
        assert "could not be computed" in fig.layout.annotations[0].text
