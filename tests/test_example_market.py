"""The Home page's examples.

The Portfolio card's picture is made-up data, but real engine output: the
Home page reads it from assets/example_portfolio.json so it loads instantly.
These tests solve the example again and check that the stored file still
matches, and that the engine's answer is PyPortfolioOpt's. The example links
must name valid symbols and objectives, or a click would open a broken form.
"""

import numpy as np
import pandas as pd
import pytest
from pypfopt import EfficientFrontier

from core.constants import MAX_TICKERS, MIN_TICKERS, OBJECTIVE_LABELS, RISK_FREE_RATE
from core.example_market import (
    EXAMPLE_PORTFOLIOS, TARGET_VOLATILITY, example_inputs, example_ohlcv, load_example,
    solve_example,
)
from utils.optimizer_wrapper import validate_inputs

REGENERATE = "stale example file; regenerate it with: python -m core.example_market"


@pytest.fixture(scope="module")
def stored():
    return load_example()


def test_stored_example_matches_a_fresh_engine_run(stored):
    fresh = solve_example()
    assert stored["objective"] == fresh["objective"], REGENERATE
    assert stored["target_volatility"] == fresh["target_volatility"], REGENERATE
    assert stored["rf"] == fresh["rf"], REGENERATE
    assert stored["portfolio"]["weights"] == pytest.approx(fresh["portfolio"]["weights"], abs=1.01e-5), REGENERATE
    for key in ("return", "volatility", "sharpe"):
        assert stored["portfolio"][key] == pytest.approx(fresh["portfolio"][key], rel=1e-7), REGENERATE


def test_example_portfolio_is_pyportfolioopts_answer(stored):
    """The picture is the reference library's result, not only the engine's."""
    mu, cov = example_inputs()
    ef = EfficientFrontier(mu, cov)
    ef.efficient_risk(target_volatility=TARGET_VOLATILITY)
    ret, vol, sharpe = ef.portfolio_performance(risk_free_rate=RISK_FREE_RATE)

    portfolio = stored["portfolio"]
    assert portfolio["weights"] == ef.clean_weights()
    np.testing.assert_allclose([portfolio["return"], portfolio["volatility"], portfolio["sharpe"]],
                               [ret, vol, sharpe], rtol=1e-9)
    assert portfolio["volatility"] == pytest.approx(TARGET_VOLATILITY, rel=1e-6)


@pytest.mark.parametrize("key", sorted(EXAMPLE_PORTFOLIOS))
def test_example_links_fill_a_valid_form(key):
    example = EXAMPLE_PORTFOLIOS[key]
    tickers = example["tickers"]

    assert MIN_TICKERS <= len(tickers) <= MAX_TICKERS
    assert validate_inputs(tickers, 10000)[0], f"{key}: rejected tickers {tickers}"
    assert example["objective"] in OBJECTIVE_LABELS
    if example["objective"] == "Maximise Return for a Given Risk":
        assert 0 < example["target_volatility"] < 1
    assert example.get("returns_estimator", "capm") in ("capm", "historical")


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
