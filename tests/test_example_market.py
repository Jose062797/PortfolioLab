"""Fig. 1 on the Home page is example data, but its numbers must still be right.

The Home page reads the solved frontier from assets/example_frontier.json so it
loads instantly. These tests solve the example market again with PyPortfolioOpt
and check that the stored file still matches, and that the random cloud the
figure draws around it never beats the frontier.
"""

import pytest

from core.example_market import load_example_frontier, random_portfolios, solve_example_frontier


def test_stored_frontier_matches_pyportfolioopt():
    """If this fails, regenerate the file: python -m core.example_market"""
    stored = load_example_frontier()
    fresh = solve_example_frontier()

    assert stored["rf"] == fresh["rf"]
    for key in ("min_variance", "max_sharpe"):
        for field in ("ret", "vol", "sharpe"):
            assert stored[key][field] == pytest.approx(fresh[key][field], rel=1e-6)
        assert stored[key]["weights"] == pytest.approx(fresh[key]["weights"], abs=1e-6)
    assert len(stored["frontier"]) == len(fresh["frontier"])
    for (vol_s, ret_s), (vol_f, ret_f) in zip(stored["frontier"], fresh["frontier"]):
        assert vol_s == pytest.approx(vol_f, rel=1e-6)
        assert ret_s == pytest.approx(ret_f, rel=1e-6)


def test_no_random_portfolio_beats_the_frontier():
    """Every random long-only portfolio lies on or below the efficient frontier."""
    data = load_example_frontier()
    frontier = sorted(data["frontier"])
    min_vol = data["min_variance"]["vol"]

    assert random_portfolios() == data["cloud"], "the seeded cloud must be reproducible"
    for vol, ret in data["cloud"]:
        assert vol >= min_vol - 1e-9
        # The frontier return rises with volatility, so the first stored point
        # at or beyond this volatility bounds what any portfolio can earn here.
        bound = next((r for v, r in frontier if v >= vol), max(data["mu"]))
        assert ret <= bound + 1e-9
