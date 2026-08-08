"""
Page-layer tests for pages/2_Portfolio.py using streamlit.testing.v1.AppTest.

This is the only layer the rest of the suite does not reach: everything the
user actually sees (conditional widgets, warnings, disabled states, captions)
lives in the Streamlit script, not in core/ or utils/.

AppTest runs the page script in-process, so the yfinance patches from
conftest.py apply exactly as they do everywhere else — these tests are
offline and deterministic like the rest of the suite.

Notably, AppTest CAN set selectbox values, which browser automation never
managed for Streamlit widgets. That is what makes the "Expected Returns
Estimator" selector verifiable at all (audit item #7).
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

PORTFOLIO_PAGE = str(Path(__file__).resolve().parents[1] / "pages" / "2_Portfolio.py")

# Optimization runs (download → estimate → solve → PDF) are well under this,
# but CI runners are slower than a dev box.
PAGE_TIMEOUT = 180


def fresh_page():
    """Load and run the Portfolio page in a clean session."""
    at = AppTest.from_file(PORTFOLIO_PAGE, default_timeout=PAGE_TIMEOUT)
    at.run()
    return at


def joined(elements):
    """Concatenate the text of an ElementList for substring assertions."""
    return "\n".join(e.value for e in elements)


def run_button(at):
    """The 'Run Optimization' button (the only button on the page pre-results)."""
    return next(b for b in at.button if b.label == "Run Optimization")


# ═══════════════════════════════════════════════════════════════════
# Empty state and ticker validation
# ═══════════════════════════════════════════════════════════════════

class TestEmptyStateAndValidation:
    """The page must guide the user before it lets them run anything."""

    def test_empty_state_prompts_and_disables_run(self):
        at = fresh_page()

        assert not at.exception
        assert "Enter 2 to 20 stock tickers" in joined(at.info)
        assert run_button(at).disabled is True

    def test_single_ticker_warns_and_keeps_run_disabled(self):
        at = fresh_page()
        at.text_input("tickers_input").set_value("AAPL").run()

        assert "at least 2 tickers" in joined(at.warning)
        assert run_button(at).disabled is True

    def test_too_many_tickers_warns_and_keeps_run_disabled(self):
        at = fresh_page()
        at.text_input("tickers_input").set_value(
            ", ".join(f"TICK{i}" for i in range(21))
        ).run()

        assert "Maximum 20 tickers allowed" in joined(at.warning)
        assert run_button(at).disabled is True

    def test_valid_ticker_count_enables_run(self):
        at = fresh_page()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()

        assert "3 tickers selected" in joined(at.success)
        assert run_button(at).disabled is False

    def test_malformed_ticker_rejected_by_validator(self, mock_yfinance_extended):
        """The allowlist must stop bad symbols before any download happens."""
        at = fresh_page()
        at.text_input("tickers_input").set_value("AAPL, BAD!TICKER").run()

        # The count check passes, so the UI lets the user press Run...
        assert run_button(at).disabled is False
        run_button(at).click().run()

        # ...and validate_inputs rejects it, naming the offending symbol.
        errors = joined(at.error)
        assert "BAD!TICKER" in errors
        assert "Invalid ticker symbol" in errors
        # Rejected before the network layer: no download was attempted.
        assert mock_yfinance_extended.call_count == 0


# ═══════════════════════════════════════════════════════════════════
# Black-Litterman × forex: hard block
# ═══════════════════════════════════════════════════════════════════

class TestBlackLittermanForexBlock:
    """
    BL builds its prior from market-cap weights; currencies have none, so the
    model is undefined for them. The page must say so AND make it unrunnable.
    """

    def test_forex_with_black_litterman_shows_error_and_disables_run(self):
        at = fresh_page()
        assert at.selectbox("model_type_select").value == "Black-Litterman"

        at.text_input("tickers_input").set_value("AAPL, EURUSD=X").run()

        errors = joined(at.error)
        assert "Black-Litterman cannot be used with forex pairs" in errors
        assert "EURUSD=X" in errors
        assert "Markowitz" in errors, "the error must point to the way out"
        assert run_button(at).disabled is True

    def test_switching_to_markowitz_unblocks_forex(self):
        at = fresh_page()
        at.text_input("tickers_input").set_value("AAPL, EURUSD=X").run()
        assert run_button(at).disabled is True

        at.selectbox("model_type_select").set_value("Markowitz").run()

        assert "cannot be used with forex pairs" not in joined(at.error)
        assert run_button(at).disabled is False

    def test_equities_with_black_litterman_are_not_blocked(self):
        at = fresh_page()
        at.text_input("tickers_input").set_value("AAPL, MSFT").run()

        assert "forex" not in joined(at.error)
        assert run_button(at).disabled is False


# ═══════════════════════════════════════════════════════════════════
# Non-equity warning and its estimator hint
# ═══════════════════════════════════════════════════════════════════

class TestNonEquityWarning:
    """Crypto is calculable but theoretically shaky — warn, never block."""

    def test_crypto_warns_but_stays_runnable(self):
        at = fresh_page()
        at.text_input("tickers_input").set_value("AAPL, BTC-USD").run()

        warnings = joined(at.warning)
        assert "Model limitation" in warnings
        assert "BTC-USD" in warnings
        assert run_button(at).disabled is False, "crypto is warned about, not blocked"

    def test_hint_recommends_historical_mean_only_under_markowitz(self):
        """
        The hint tells the user to switch estimator — advice that only makes
        sense when the estimator selector exists (Markowitz).
        """
        at = fresh_page()
        at.text_input("tickers_input").set_value("AAPL, BTC-USD").run()

        # Black-Litterman: warning present, but no estimator to switch to.
        assert "Historical mean" not in joined(at.warning)

        at.selectbox("model_type_select").set_value("Markowitz").run()

        warnings = joined(at.warning)
        assert "Advanced Optimization Settings" in warnings
        assert "Historical mean" in warnings

    def test_forex_under_markowitz_also_gets_the_hint(self):
        at = fresh_page()
        at.selectbox("model_type_select").set_value("Markowitz").run()
        at.text_input("tickers_input").set_value("AAPL, EURUSD=X").run()

        assert "Historical mean" in joined(at.warning)


# ═══════════════════════════════════════════════════════════════════
# Expected Returns Estimator selector (audit items #4 + #7)
# ═══════════════════════════════════════════════════════════════════

class TestReturnsEstimatorSelector:
    """
    The selector was never verifiable in a browser (Streamlit selectbox values
    never reached the server under automation). AppTest closes that gap.
    """

    def test_selector_exists_only_for_markowitz(self):
        at = fresh_page()
        keys = [s.key for s in at.selectbox]
        assert "returns_estimator_select" not in keys, "BL has no CAPM estimator choice"

        at.selectbox("model_type_select").set_value("Markowitz").run()

        keys = [s.key for s in at.selectbox]
        assert "returns_estimator_select" in keys
        assert at.selectbox("returns_estimator_select").value.startswith("CAPM"), \
            "cookbook default must stay the default"

    def test_selected_estimator_reaches_the_engine(self, mock_yfinance_extended):
        """
        Not just that the widget accepts the value — that the choice travels
        UI → wrapper → engine and actually changes the optimization.

        Max Sharpe is used deliberately: Min Variance ignores expected
        returns entirely, so it could not tell the two estimators apart.
        """
        def optimize_with(estimator_label):
            at = fresh_page()
            at.selectbox("model_type_select").set_value("Markowitz").run()
            at.selectbox("obj_function_select").set_value("Max Sharpe").run()
            at.selectbox("returns_estimator_select").set_value(estimator_label).run()
            at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
            run_button(at).click().run()

            assert not at.exception
            result = at.session_state["optimization_result"]
            assert result["success"], result.get("error")
            return result

        capm = optimize_with("CAPM vs. market (cookbook default)")
        historical = optimize_with("Historical mean")

        assert capm["returns_estimator"] == "capm"
        assert historical["returns_estimator"] == "historical"

        # The real proof: a different estimator produces a different portfolio.
        assert capm["weights"] != historical["weights"], (
            "estimator choice did not change the optimization — the value is "
            "not reaching calculate_markowitz_inputs"
        )


# ═══════════════════════════════════════════════════════════════════
# Results-panel notices
# ═══════════════════════════════════════════════════════════════════

class TestOverlapNotice:
    """
    Near-duplicate holdings (VOO/IVV) look like diversification to the
    optimizer but are not. The notice must use empirical correlation —
    Ledoit-Wolf shrinkage pushes the pair below the 0.95 threshold.
    """

    # Same universe for both cases below, so the only variable is the pair.
    UNIVERSE = "VOO, IVV, AAPL, MSFT, GOOGL"

    def test_fixture_discriminates_empirical_from_shrunk_correlation(
        self, extended_prices
    ):
        """
        Guard for the tests below, not for the app.

        The detector must read empirical correlation; reading the stored
        Ledoit-Wolf covariance instead is the documented trap (real VOO/IVV:
        0.9997 empirical vs ~0.949 shrunk — under the threshold). These
        tests can only catch that regression while the fixture reproduces
        the gap, so assert the gap explicitly: if a future fixture edit
        collapses it, this fails loudly instead of quietly weakening the
        suite.
        """
        import numpy as np
        from pypfopt import risk_models

        prices = extended_prices[[t.strip() for t in self.UNIVERSE.split(",")]]

        empirical = prices.pct_change().corr().loc["VOO", "IVV"]
        cov = risk_models.CovarianceShrinkage(prices).ledoit_wolf()
        std = np.sqrt(np.diag(cov))
        shrunk = (cov / np.outer(std, std)).loc["VOO", "IVV"]

        assert empirical >= 0.95, "fixture no longer models overlapping holdings"
        assert shrunk < 0.95, (
            f"shrunk correlation is {shrunk:.4f} — still above the threshold, so "
            "the overlap tests would pass even if the detector regressed to the "
            "stored covariance"
        )

    def test_near_duplicate_etfs_trigger_overlap_notice(self, mock_yfinance_extended):
        at = fresh_page()
        at.selectbox("model_type_select").set_value("Markowitz").run()
        at.text_input("tickers_input").set_value(self.UNIVERSE).run()
        run_button(at).click().run()

        assert not at.exception
        assert at.session_state["optimization_result"]["success"]

        infos = joined(at.info)
        assert "Possible overlapping holdings" in infos
        assert "VOO" in infos and "IVV" in infos

    def test_distinct_assets_do_not_trigger_overlap_notice(self, mock_yfinance_extended):
        at = fresh_page()
        at.selectbox("model_type_select").set_value("Markowitz").run()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
        run_button(at).click().run()

        assert not at.exception
        assert "Possible overlapping holdings" not in joined(at.info)


class TestAllocationMethodCaption:
    """
    The greedy fallback used to be invisible outside the server log.

    The caption is asserted by toggling the stored flag rather than by
    forcing a solver failure: whether ECOS_BB is installed differs between
    the dev box (no cp314 wheel → greedy) and CI on 3.12 (→ lp), and a test
    that depends on that would be flaky. What belongs to the page layer is
    the wiring from allocation_method to the caption, which is what this
    checks in both directions.
    """

    CAPTION_MARK = "greedy method"

    def _run_once(self, at):
        at.selectbox("model_type_select").set_value("Markowitz").run()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
        run_button(at).click().run()
        assert at.session_state["optimization_result"]["success"]

    def test_caption_shown_when_greedy_and_hidden_when_lp(self, mock_yfinance_extended):
        at = fresh_page()
        self._run_once(at)

        at.session_state["optimization_result"]["allocation_method"] = "greedy"
        at.run()
        assert self.CAPTION_MARK in joined(at.caption), \
            "greedy fallback must be surfaced to the user, not just logged"

        at.session_state["optimization_result"]["allocation_method"] = "lp"
        at.run()
        assert self.CAPTION_MARK not in joined(at.caption), \
            "the exact LP allocation must not be labelled as a fallback"


# ═══════════════════════════════════════════════════════════════════
# Results panel: the happy path renders
# ═══════════════════════════════════════════════════════════════════

class TestResultsPanel:

    def test_successful_run_renders_metrics_and_tabs(self, mock_yfinance_extended):
        at = fresh_page()
        at.selectbox("model_type_select").set_value("Markowitz").run()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
        run_button(at).click().run()

        assert not at.exception
        assert "Optimization completed successfully" in joined(at.success)

        labels = [m.label for m in at.metric]
        for expected in ["Expected Return", "Volatility", "Sharpe Ratio", "Assets"]:
            assert expected in labels

    def test_markowitz_swaps_returns_analysis_for_efficient_frontier(
        self, mock_yfinance_extended
    ):
        """Tab set is model-dependent (see CLAUDE.md → Web Tabs)."""
        at = fresh_page()
        at.selectbox("model_type_select").set_value("Markowitz").run()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
        run_button(at).click().run()

        headings = joined(at.markdown)
        assert "Efficient Frontier" in headings
        assert "### Returns Analysis" not in headings
