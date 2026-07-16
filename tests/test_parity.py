"""
Parity suite: engine output vs raw PyPortfolioOpt (cookbook-style code).

Each test builds the same portfolio twice — once through core.opt_engine and
once with direct PyPortfolioOpt calls exactly as the cookbook notebooks do —
and asserts the results are identical. This is the permanent regression
guard for the project's core promise: the engine adds no mathematical
deviation over the reference library.

Runs fully offline on the synthetic fixtures from conftest.py.
"""

import numpy as np
import pandas as pd
import pytest

import pypfopt
from pypfopt import EfficientFrontier, BlackLittermanModel, objective_functions
from pypfopt import risk_models, expected_returns, black_litterman

from core.constants import RISK_FREE_RATE
from core.opt_engine import (
    calculate_prior,
    run_black_litterman,
    calculate_markowitz_inputs,
    optimize_portfolio,
)


@pytest.fixture
def portfolio_prices(synthetic_prices, sample_mcaps):
    """Prices for the 3 portfolio tickers only (no SPY)."""
    return synthetic_prices[list(sample_mcaps.keys())]


@pytest.fixture
def spy_prices(synthetic_prices):
    return synthetic_prices["SPY"]


def assert_weights_identical(engine_weights, raw_weights):
    """Cleaned weight dicts must match exactly, ticker by ticker."""
    assert set(engine_weights.keys()) == set(raw_weights.keys())
    for ticker in raw_weights:
        assert engine_weights[ticker] == raw_weights[ticker], (
            f"{ticker}: engine={engine_weights[ticker]} raw={raw_weights[ticker]}"
        )


def assert_performance_identical(engine_metrics, raw_perf):
    ret, vol, sharpe = raw_perf
    np.testing.assert_allclose(engine_metrics["expected_return"], ret, rtol=1e-12)
    np.testing.assert_allclose(engine_metrics["volatility"], vol, rtol=1e-12)
    np.testing.assert_allclose(engine_metrics["sharpe_ratio"], sharpe, rtol=1e-12)


class TestBlackLittermanParity:
    def test_prior_parity(self, portfolio_prices, spy_prices, sample_mcaps):
        """calculate_prior == raw cookbook prior (S, delta, market prior)."""
        S_eng, delta_eng, prior_eng, _ = calculate_prior(
            portfolio_prices, spy_prices, sample_mcaps
        )

        S_raw = risk_models.CovarianceShrinkage(portfolio_prices).ledoit_wolf()
        delta_raw = black_litterman.market_implied_risk_aversion(spy_prices)
        prior_raw = black_litterman.market_implied_prior_returns(
            sample_mcaps, delta_raw, S_raw
        )

        pd.testing.assert_frame_equal(S_eng, S_raw)
        assert delta_eng == delta_raw
        pd.testing.assert_series_equal(prior_eng, prior_raw)

    def test_no_views_posterior_equals_prior(
        self, portfolio_prices, spy_prices, sample_mcaps
    ):
        """Without views the engine must return the prior untouched."""
        S, delta, prior, _ = calculate_prior(portfolio_prices, spy_prices, sample_mcaps)
        bl, ret_bl, S_bl = run_black_litterman(S, delta, sample_mcaps, prior, None, None)

        assert bl is None
        pd.testing.assert_series_equal(ret_bl, prior)
        pd.testing.assert_frame_equal(S_bl, S)

    def test_views_posterior_parity(self, portfolio_prices, spy_prices, sample_mcaps):
        """BL with views == raw BlackLittermanModel with the same omega."""
        viewdict = {"AAPL": 0.15, "GOOGL": 0.05}
        intervals = {"AAPL": (0.10, 0.20), "GOOGL": (0.00, 0.10)}

        S, delta, prior, _ = calculate_prior(portfolio_prices, spy_prices, sample_mcaps)
        _, ret_bl_eng, S_bl_eng = run_black_litterman(
            S, delta, sample_mcaps, prior, viewdict, intervals
        )

        # Raw cookbook path: omega from interval half-widths, sigma=(u-l)/2
        variances = [((u - l) / 2) ** 2 for (l, u) in intervals.values()]
        omega = np.diag(variances)
        bl_raw = BlackLittermanModel(
            S,
            pi="market",
            market_caps=sample_mcaps,
            risk_aversion=delta,
            absolute_views=viewdict,
            omega=omega,
        )
        ret_bl_raw = bl_raw.bl_returns()
        S_bl_raw = bl_raw.bl_cov()

        pd.testing.assert_series_equal(ret_bl_eng, ret_bl_raw)
        pd.testing.assert_frame_equal(S_bl_eng, S_bl_raw)


class TestMarkowitzInputsParity:
    def test_capm_and_ledoit_wolf_parity(self, portfolio_prices, spy_prices):
        """calculate_markowitz_inputs == raw capm_return + ledoit_wolf."""
        mu_eng, S_eng = calculate_markowitz_inputs(portfolio_prices, spy_prices)

        mu_raw = expected_returns.capm_return(
            portfolio_prices, market_prices=spy_prices, risk_free_rate=RISK_FREE_RATE
        )
        S_raw = risk_models.CovarianceShrinkage(portfolio_prices).ledoit_wolf()

        pd.testing.assert_series_equal(mu_eng, mu_raw)
        pd.testing.assert_frame_equal(S_eng, S_raw)


class TestOptimizationParity:
    """The four objectives + L2, engine vs raw EfficientFrontier."""

    @pytest.fixture
    def mu_S(self, portfolio_prices, spy_prices):
        return calculate_markowitz_inputs(portfolio_prices, spy_prices)

    def test_min_variance_parity(self, mu_S):
        mu, S = mu_S
        w_eng, m_eng = optimize_portfolio(mu, S, obj_function="Min Variance")

        ef = EfficientFrontier(mu, S)
        ef.min_volatility()
        w_raw = ef.clean_weights()
        perf_raw = ef.portfolio_performance(risk_free_rate=RISK_FREE_RATE)

        assert_weights_identical(w_eng, w_raw)
        assert_performance_identical(m_eng, perf_raw)

    def test_max_sharpe_parity(self, mu_S):
        mu, S = mu_S
        w_eng, m_eng = optimize_portfolio(mu, S, obj_function="Max Sharpe")

        ef = EfficientFrontier(mu, S)
        ef.max_sharpe(risk_free_rate=RISK_FREE_RATE)
        w_raw = ef.clean_weights()
        perf_raw = ef.portfolio_performance(risk_free_rate=RISK_FREE_RATE)

        assert_weights_identical(w_eng, w_raw)
        assert_performance_identical(m_eng, perf_raw)

    def test_efficient_risk_parity(self, mu_S):
        mu, S = mu_S
        target_vol = 0.20
        w_eng, m_eng = optimize_portfolio(
            mu, S, obj_function="Maximise Return for a Given Risk",
            target_volatility=target_vol,
        )

        ef = EfficientFrontier(mu, S)
        ef.efficient_risk(target_volatility=target_vol)
        w_raw = ef.clean_weights()
        perf_raw = ef.portfolio_performance(risk_free_rate=RISK_FREE_RATE)

        assert_weights_identical(w_eng, w_raw)
        assert_performance_identical(m_eng, perf_raw)

    def test_efficient_return_parity(self, mu_S):
        mu, S = mu_S
        # Midpoint of achievable returns — the synthetic CAPM returns sit
        # close to the risk-free rate, so a fixed 10% would be infeasible.
        target_ret = float(mu.min() + (mu.max() - mu.min()) / 2)
        w_eng, m_eng = optimize_portfolio(
            mu, S, obj_function="Minimise Risk for a Given Return",
            target_return=target_ret,
        )

        ef = EfficientFrontier(mu, S)
        ef.efficient_return(target_return=target_ret)
        w_raw = ef.clean_weights()
        perf_raw = ef.portfolio_performance(risk_free_rate=RISK_FREE_RATE)

        assert_weights_identical(w_eng, w_raw)
        assert_performance_identical(m_eng, perf_raw)

    def test_l2_regularization_parity(self, mu_S):
        """L2 gamma applied before the objective, exactly like the BL cookbook."""
        mu, S = mu_S
        gamma = 1.0
        w_eng, m_eng = optimize_portfolio(
            mu, S, obj_function="Min Variance", l2_gamma=gamma
        )

        ef = EfficientFrontier(mu, S)
        ef.add_objective(objective_functions.L2_reg, gamma=gamma)
        ef.min_volatility()
        w_raw = ef.clean_weights()
        perf_raw = ef.portfolio_performance(risk_free_rate=RISK_FREE_RATE)

        assert_weights_identical(w_eng, w_raw)
        assert_performance_identical(m_eng, perf_raw)

    def test_bl_end_to_end_parity(self, portfolio_prices, spy_prices, sample_mcaps):
        """Full BL pipeline with views + L2, engine vs raw, end to end."""
        viewdict = {"MSFT": 0.12}
        intervals = {"MSFT": (0.08, 0.16)}
        gamma = 1.0

        # Engine path
        S, delta, prior, _ = calculate_prior(portfolio_prices, spy_prices, sample_mcaps)
        _, ret_bl, S_bl = run_black_litterman(
            S, delta, sample_mcaps, prior, viewdict, intervals
        )
        w_eng, m_eng = optimize_portfolio(
            ret_bl, S_bl, obj_function="Max Sharpe", l2_gamma=gamma
        )

        # Raw cookbook path
        S_raw = risk_models.CovarianceShrinkage(portfolio_prices).ledoit_wolf()
        delta_raw = black_litterman.market_implied_risk_aversion(spy_prices)
        omega = np.diag([((0.16 - 0.08) / 2) ** 2])
        bl = BlackLittermanModel(
            S_raw, pi="market", market_caps=sample_mcaps,
            risk_aversion=delta_raw, absolute_views=viewdict, omega=omega,
        )
        ef = EfficientFrontier(bl.bl_returns(), bl.bl_cov())
        ef.add_objective(objective_functions.L2_reg, gamma=gamma)
        ef.max_sharpe(risk_free_rate=RISK_FREE_RATE)
        w_raw = ef.clean_weights()
        perf_raw = ef.portfolio_performance(risk_free_rate=RISK_FREE_RATE)

        assert_weights_identical(w_eng, w_raw)
        assert_performance_identical(m_eng, perf_raw)
