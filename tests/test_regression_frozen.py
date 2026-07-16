"""
Frozen-value regression tests (audit D4.3).

These values were computed on 2026-07-16 under Python 3.14.5,
pandas 3.0.3, numpy 2.5.1, PyPortfolioOpt 1.5.6, cvxpy 1.9.2 — a stack
whose parity with raw PyPortfolioOpt was verified by tests/test_parity.py
and whose behaviour matched the MIT reference scenarios of
GUIA_TESTEO_MANUAL.txt.

If any of these tests fail after a dependency upgrade, the numbers have
silently changed: re-run the parity suite and the manual-guide scenarios
before accepting new values.
"""

import pytest

from core.opt_engine import (
    calculate_markowitz_inputs,
    optimize_portfolio,
    calculate_prior,
    run_black_litterman,
)


@pytest.fixture
def portfolio_prices(synthetic_prices, sample_mcaps):
    return synthetic_prices[list(sample_mcaps.keys())]


@pytest.fixture
def spy_prices(synthetic_prices):
    return synthetic_prices["SPY"]


class TestFrozenMarkowitz:
    def test_min_variance_snapshot(self, portfolio_prices, spy_prices):
        mu, S = calculate_markowitz_inputs(portfolio_prices, spy_prices)
        weights, metrics = optimize_portfolio(mu, S, obj_function="Min Variance")

        # clean_weights rounds to 5 decimals → exact equality expected
        assert weights == {"AAPL": 0.37805, "MSFT": 0.39184, "GOOGL": 0.23011}

        assert metrics["expected_return"] == pytest.approx(0.03143830897815714, rel=1e-9)
        assert metrics["volatility"] == pytest.approx(0.13709194226351787, rel=1e-9)
        assert metrics["sharpe_ratio"] == pytest.approx(0.010491564671192877, rel=1e-6)


class TestFrozenBlackLitterman:
    def test_bl_with_view_snapshot(self, portfolio_prices, spy_prices, sample_mcaps):
        S0, delta, prior, _ = calculate_prior(portfolio_prices, spy_prices, sample_mcaps)

        assert float(delta) == pytest.approx(5.849548710847318, rel=1e-9)

        viewdict = {"AAPL": 0.15}
        intervals = {"AAPL": (0.10, 0.20)}
        _, posterior, S_bl = run_black_litterman(
            S0, delta, sample_mcaps, prior, viewdict, intervals
        )

        assert float(posterior["AAPL"]) == pytest.approx(0.12675524842219862, rel=1e-9)
        assert float(posterior["MSFT"]) == pytest.approx(0.11014517615665602, rel=1e-9)
        assert float(posterior["GOOGL"]) == pytest.approx(0.11992424628655535, rel=1e-9)

        weights, metrics = optimize_portfolio(
            posterior, S_bl, obj_function="Max Sharpe", l2_gamma=1.0
        )
        assert weights == {"AAPL": 0.3666, "MSFT": 0.30333, "GOOGL": 0.33007}
        assert metrics["expected_return"] == pytest.approx(0.11946217055022004, rel=1e-9)
        assert metrics["volatility"] == pytest.approx(0.14407665288662633, rel=1e-9)
        assert metrics["sharpe_ratio"] == pytest.approx(0.6209345425356159, rel=1e-9)
