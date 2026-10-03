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

import time
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
    """The 'Run optimization' button (the only button on the page pre-results)."""
    return next(b for b in at.button if b.label == "Run optimization")


def black_litterman(at):
    """Switch the model to Black-Litterman (the page opens on Markowitz)."""
    at.selectbox("model_type_select").set_value("Black-Litterman").run()
    return at


def notes_text(at):
    """The 'Notes about these results' box: its label and its text. It is an
    st.expander with an icon, which AppTest lists under at.status."""
    boxes = [e for e in list(at.expander) + list(at.status)
             if e.label.startswith("Notes about these results")]
    return "\n".join([e.label for e in boxes] + [joined(e.markdown) for e in boxes])


# ═══════════════════════════════════════════════════════════════════
# Empty state and ticker validation
# ═══════════════════════════════════════════════════════════════════

class TestEmptyStateAndValidation:
    """The page must guide the user before it lets them run anything."""

    def test_empty_state_prompts_and_disables_run(self):
        at = fresh_page()

        assert not at.exception
        # Markowitz first: it needs no market capitalizations (rate-limited on the cloud)
        assert at.selectbox("model_type_select").value == "Markowitz"
        assert "2 to 20 symbols" in joined(at.caption)
        assert not at.warning, "an empty form is not a mistake"
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

        assert "20 tickers at most" in joined(at.warning)
        assert run_button(at).disabled is True

    def test_valid_ticker_count_enables_run(self):
        at = fresh_page()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()

        assert not at.warning
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
        at = black_litterman(fresh_page())
        at.text_input("tickers_input").set_value("AAPL, EURUSD=X").run()

        errors = joined(at.error)
        assert "Black-Litterman cannot be used with forex pairs" in errors
        assert "EURUSD=X" in errors
        assert "Markowitz" in errors, "the error must point to the way out"
        assert run_button(at).disabled is True

    def test_switching_to_markowitz_unblocks_forex(self):
        at = black_litterman(fresh_page())
        at.text_input("tickers_input").set_value("AAPL, EURUSD=X").run()
        assert run_button(at).disabled is True

        at.selectbox("model_type_select").set_value("Markowitz").run()

        assert "cannot be used with forex pairs" not in joined(at.error)
        assert run_button(at).disabled is False

    def test_equities_with_black_litterman_are_not_blocked(self):
        at = black_litterman(fresh_page())
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
        assert "BTC-USD is not a stock" in warnings
        assert run_button(at).disabled is False, "crypto is warned about, not blocked"

    def test_hint_recommends_historical_mean_only_under_markowitz(self):
        """
        The hint tells the user to switch estimator — advice that only makes
        sense when the estimator selector exists (Markowitz).
        """
        at = black_litterman(fresh_page())
        at.text_input("tickers_input").set_value("AAPL, BTC-USD").run()

        # Black-Litterman: warning present, but no estimator to switch to.
        assert "Historical mean" not in joined(at.warning)

        at.selectbox("model_type_select").set_value("Markowitz").run()

        warnings = joined(at.warning)
        assert "Advanced settings" in warnings
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
        at = black_litterman(fresh_page())
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

        notes = notes_text(at)
        assert "Overlapping holdings" in notes
        assert "VOO" in notes and "IVV" in notes

    def test_distinct_assets_do_not_trigger_overlap_notice(self, mock_yfinance_extended):
        at = fresh_page()
        at.selectbox("model_type_select").set_value("Markowitz").run()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
        run_button(at).click().run()

        assert not at.exception
        assert "Overlapping holdings" not in notes_text(at)


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

        labels = [m.label for m in at.metric]
        for expected in ["Expected return", "Volatility", "Sharpe ratio", "Budget", "Assets"]:
            assert expected in labels

    def test_results_page_does_not_build_the_pdf(self, mock_yfinance_extended, monkeypatch):
        """The PDF is built on click (deferred download), never on a rerun."""
        calls = []
        monkeypatch.setattr("utils.pdf_generator.generate_portfolio_pdf",
                            lambda *a, **k: calls.append(1) or b"%PDF-")
        at = fresh_page()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
        run_button(at).click().run()
        at.run()

        assert not at.exception
        assert at.session_state["optimization_result"]["success"]
        assert calls == []

    def test_markowitz_swaps_returns_analysis_for_efficient_frontier(
        self, mock_yfinance_extended
    ):
        """Tab set is model-dependent (see CLAUDE.md → Web Tabs)."""
        at = fresh_page()
        at.selectbox("model_type_select").set_value("Markowitz").run()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
        run_button(at).click().run()

        tabs = [t.label for t in at.tabs]
        assert tabs == ["Allocation", "Efficient frontier", "Historical performance",
                        "Correlation", "Details"]

    def test_details_name_the_goal_in_plain_words_and_its_target(self, mock_yfinance_extended):
        at = fresh_page()
        at.selectbox("model_type_select").set_value("Markowitz").run()
        at.selectbox("obj_function_select").set_value("Maximise Return for a Given Risk").run()
        at.number_input("target_volatility_pct").set_value(25.0).run()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
        run_button(at).click().run()

        assert not at.exception
        result = at.session_state["optimization_result"]
        assert result["success"], result.get("error")
        # The form takes a percentage; the engine a fraction
        assert result["target_volatility"] == 0.25
        assert ("Highest return within a risk limit of 25% (Maximise Return for a Given Risk)"
                in joined(at.markdown))


# ═══════════════════════════════════════════════════════════════════
# Black-Litterman without market caps: say why, point to Markowitz
# ═══════════════════════════════════════════════════════════════════

class TestMarketSizeErrors:
    """Black-Litterman needs every asset's market cap. Yahoo rate-limits that
    request from shared cloud servers (seen in production on 2026-09-26) and
    some symbols have none. The inputs are fine in both cases, so the message
    must not blame them, and it must point to Markowitz, which needs no caps."""

    @pytest.mark.parametrize("last_error, headline", [
        ("Too Many Requests. Rate limited. Try after a while.",
         "Market data temporarily unavailable"),
        ("neither totalAssets nor marketCap available for 'AAPL'",
         "No market capitalization available"),
    ])
    def test_market_size_failure_points_to_markowitz(self, monkeypatch, last_error, headline):
        # The message download_market_caps raises, as run_optimization returns it
        error = (
            "Could not fetch market size for 'AAPL' after 3 attempts. Yahoo Finance "
            "may be rate-limiting — please try again in a moment. "
            f"(Last error: {last_error})"
        )
        monkeypatch.setattr(
            "utils.optimizer_wrapper.run_optimization",
            lambda **kwargs: {"success": False, "error": error},
        )
        at = black_litterman(fresh_page())
        at.text_input("tickers_input").set_value("AAPL, MSFT").run()
        run_button(at).click().run()

        errors = joined(at.error)
        assert headline in errors
        assert "Markowitz" in errors
        assert "check your inputs" not in errors


# ═══════════════════════════════════════════════════════════════════
# Prices in another currency: warn, never block
# ═══════════════════════════════════════════════════════════════════

class TestCurrencyWarning:
    """PortfolioLab treats every price as US dollars, so share counts for a
    listing in euros or yen are wrong. Yahoo marks those with an exchange
    suffix after a dot (SAP.DE); US share classes use a dash (BRK-B)."""

    @pytest.mark.parametrize("tickers, flagged", [
        ("SAP.DE, AAPL", "SAP.DE"),
        ("7203.T, AAPL", "7203.T"),
        ("BTC-EUR, AAPL", "BTC-EUR"),
    ])
    def test_non_dollar_prices_are_flagged(self, tickers, flagged):
        at = fresh_page()
        at.text_input("tickers_input").set_value(tickers).run()

        warnings = joined(at.warning)
        assert f"{flagged} is priced in another currency" in warnings
        assert run_button(at).disabled is False

    @pytest.mark.parametrize("tickers", ["BRK-B, AAPL", "BTC-USD, AAPL", "AAPL, MSFT"])
    def test_dollar_prices_are_not_flagged(self, tickers):
        at = fresh_page()
        at.text_input("tickers_input").set_value(tickers).run()

        assert "another currency" not in joined(at.warning)


# ═══════════════════════════════════════════════════════════════════
# Data notes: known distortions in the estimates, shown with a remedy
# ═══════════════════════════════════════════════════════════════════

class TestDataNotes:
    """The wrapper records late-listed assets and mixed weekend calendars
    (utils/optimizer_wrapper._data_notes), which shorten the estimation
    window; the page must say so. The notes are set on the stored result so
    the wiring is tested directly."""

    def test_notes_shown_only_when_present(self, mock_yfinance_extended):
        at = fresh_page()
        at.selectbox("model_type_select").set_value("Markowitz").run()
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
        run_button(at).click().run()
        assert at.session_state["optimization_result"]["success"]

        # Nothing to note: no notes box at all
        assert notes_text(at) == ""

        at.session_state["optimization_result"]["data_notes"] = {
            "data_start": "2020-01-02",
            "late_assets": [("GOOGL", "2022-06-01")],
            "mixed_calendar": True,
        }
        at.run()

        notes = notes_text(at)
        assert "Notes about these results (2)" in notes
        assert "Shorter common history" in notes
        assert "GOOGL" in notes and "2022-06-01" in notes
        assert "Weekend prices" in notes


# ═══════════════════════════════════════════════════════════════════
# Home page example links: ./Portfolio?example=<key> fills the form
# ═══════════════════════════════════════════════════════════════════

class TestExampleLinks:
    """Each Home card links here with ?example=<key>. The form must be filled
    in exactly as the example says, once, and never run by itself."""

    def open_example(self, key):
        at = AppTest.from_file(PORTFOLIO_PAGE, default_timeout=PAGE_TIMEOUT)
        at.query_params["example"] = key
        at.run()
        return at

    def test_example_fills_the_form(self):
        at = self.open_example("stocks-bonds-gold")

        assert not at.exception
        assert at.text_input("tickers_input").value == "VTI, AGG, GLD"
        assert at.selectbox("model_type_select").value == "Markowitz"
        assert at.selectbox("obj_function_select").value == "Maximise Return for a Given Risk"
        assert at.number_input("target_volatility_pct").value == 10.0
        assert at.selectbox("returns_estimator_select").value == "Historical mean"
        assert run_button(at).disabled is False
        assert at.session_state["optimization_result"] is None, "the user presses Run"

    def test_example_applies_once(self):
        """The parameter leaves the URL, so the next rerun keeps the user's edits."""
        at = self.open_example("big-tech")
        assert "example" not in at.query_params

        at.text_input("tickers_input").set_value("AAPL, MSFT").run()
        assert at.text_input("tickers_input").value == "AAPL, MSFT"

    def test_unknown_example_leaves_the_form_empty(self):
        at = self.open_example("no-such-example")

        assert not at.exception
        assert at.text_input("tickers_input").value == ""


# ═══════════════════════════════════════════════════════════════════
# Black-Litterman views: typed in percent, passed on as fractions
# ═══════════════════════════════════════════════════════════════════

class TestViewsInPercent:

    def test_views_reach_the_engine_as_fractions(self, mock_yfinance_extended, monkeypatch):
        # Skip the engine's pacing between market-cap requests (whole seconds),
        # but keep short sleeps: AppTest waits for the page with
        # time.sleep(0.001), and a blanket no-op turned that wait into a busy
        # loop that starved the page's thread (5 minutes, then a timeout).
        real_sleep = time.sleep
        monkeypatch.setattr("time.sleep", lambda seconds: real_sleep(seconds) if seconds < 0.5 else None)
        at = black_litterman(fresh_page())
        at.text_input("tickers_input").set_value("AAPL, MSFT, GOOGL").run()
        at.checkbox("add_views_checkbox").check().run()
        at.multiselect("selected_views_ms").select("AAPL").run()
        at.number_input("exp_AAPL").set_value(12.0).run()
        at.number_input("low_AAPL").set_value(8.0).run()
        at.number_input("upp_AAPL").set_value(16.0).run()
        run_button(at).click().run()

        assert not at.exception
        result = at.session_state["optimization_result"]
        assert result["success"], result.get("error")
        assert result["viewdict"] == {"AAPL": 0.12}
        assert result["views_detail"]["AAPL"] == {"expected": 0.12, "lower": 0.08, "upper": 0.16}
