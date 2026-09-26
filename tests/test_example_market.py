"""The Home page's example figures are made-up data, but real engine output.

The Home page reads the engine's results from assets/example_frontier.json so
it loads instantly. These tests solve the example again and check that the
stored file still matches, that the engine and PyPortfolioOpt agree on it (the
Home page's parity table says they do), and that the frontier it draws is
really efficient.
"""

import numpy as np
import pandas as pd
import pytest
import pypfopt

from core.example_market import COV, MU, example_ohlcv, load_example, solve_example

REGENERATE = "stale example file; regenerate it with: python -m core.example_market"


@pytest.fixture(scope="module")
def stored():
    return load_example()


@pytest.fixture(scope="module")
def fresh():
    return solve_example()


def test_stored_example_matches_a_fresh_engine_run(stored, fresh):
    assert stored["objective"] == fresh["objective"], REGENERATE
    assert stored["rf"] == fresh["rf"], REGENERATE
    for side in ("portfolio", "reference"):
        assert stored[side]["weights"] == pytest.approx(fresh[side]["weights"], abs=1.01e-5), REGENERATE
        for key in ("return", "volatility", "sharpe"):
            assert stored[side][key] == pytest.approx(fresh[side][key], rel=1e-7), REGENERATE

    ef_stored, ef_fresh = stored["ef_data"], fresh["ef_data"]
    assert ef_stored.keys() == ef_fresh.keys(), REGENERATE
    assert len(ef_stored["mus"]) == len(ef_fresh["mus"]), REGENERATE
    for key in ("mus", "sigmas"):
        assert ef_stored[key] == pytest.approx(ef_fresh[key], rel=1e-6), REGENERATE
    for key in ("optimal_ret", "optimal_risk", "sharpe_max", "min_vol_ret", "min_vol_risk"):
        assert ef_stored[key] == pytest.approx(ef_fresh[key], rel=1e-7), REGENERATE
    for key in ("asset_mu", "asset_sigma"):
        assert ef_stored[key] == pytest.approx(ef_fresh[key], rel=1e-12), REGENERATE


def test_stored_example_was_solved_with_the_installed_pyportfolioopt(stored):
    """The parity table names the library version that produced its numbers."""
    assert stored["pypfopt_version"] == pypfopt.__version__, REGENERATE


def test_engine_and_pyportfolioopt_agree_on_the_example(stored, fresh):
    """What the Home page's parity table shows: same weights, same metrics."""
    for data in (stored, fresh):
        engine, reference = data["portfolio"], data["reference"]
        assert engine["weights"] == reference["weights"]
        for key in ("return", "volatility", "sharpe"):
            np.testing.assert_allclose(engine[key], reference[key], rtol=1e-12)


def test_selected_portfolio_sits_on_the_frontier_at_its_target_risk(stored):
    """Fig. 1's amber marker: on the frontier, at the target volatility, below Max Sharpe."""
    ef, portfolio = stored["ef_data"], stored["portfolio"]
    vol, ret = portfolio["volatility"], portfolio["return"]
    assert vol == pytest.approx(stored["target_volatility"], rel=1e-6)

    # Between its two neighboring frontier points, and not below their chord:
    # the frontier is concave, so it runs above the straight line between them.
    points = sorted(zip(ef["sigmas"], ef["mus"]))
    (s0, m0), (s1, m1) = max(p for p in points if p[0] <= vol), min(p for p in points if p[0] >= vol)
    assert m0 - 1e-9 <= ret <= m1 + 1e-9
    assert ret >= m0 + (m1 - m0) * (vol - s0) / (s1 - s0) - 1e-9
    assert portfolio["sharpe"] < ef["sharpe_max"]


def test_frontier_is_efficient(stored):
    """No frontier point beats Max Sharpe or Min Variance, and random portfolios stay below it."""
    ef, rf = stored["ef_data"], stored["rf"]
    points = sorted(zip(ef["sigmas"], ef["mus"]))

    for sigma, mu in points:
        assert sigma >= ef["min_vol_risk"] - 1e-7
        assert (mu - rf) / sigma <= ef["sharpe_max"] + 1e-7

    # The frontier's return rises with volatility, so the first stored point at
    # or beyond a portfolio's volatility bounds what that portfolio can earn.
    rng = np.random.default_rng(42)
    for _ in range(2000):
        w = rng.dirichlet(np.ones(len(MU)) * rng.choice([0.2, 1.0]))
        vol, ret = float(np.sqrt(w @ COV @ w)), float(w @ MU)
        assert vol >= ef["min_vol_risk"] - 1e-7
        bound = next((m for s, m in points if s >= vol), float(MU.max()))
        assert ret <= bound + 1e-7


def test_example_ohlcv_is_a_valid_year_of_daily_bars():
    ohlcv = example_ohlcv()

    assert list(ohlcv.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(ohlcv) == 252
    assert isinstance(ohlcv.index, pd.DatetimeIndex)
    assert ohlcv.index.is_monotonic_increasing and (ohlcv.index.dayofweek < 5).all()
    assert (ohlcv["High"] >= ohlcv[["Open", "Close"]].max(axis=1)).all()
    assert (ohlcv["Low"] <= ohlcv[["Open", "Close"]].min(axis=1)).all()
    assert (ohlcv[["Open", "High", "Low", "Close"]] > 0).all().all()
    assert (ohlcv["Volume"] > 0).all()
    pd.testing.assert_frame_equal(ohlcv, example_ohlcv())
