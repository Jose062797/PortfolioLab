"""
Example market for Fig. 1 on the Home page: five illustrative assets.

Not market data (the page labels it "Example data"). The expected returns,
volatilities and correlations below are made up to draw a readable efficient
frontier with a 3 % risk-free rate.

The long-only frontier, Min Variance and Max Sharpe portfolios are solved with
PyPortfolioOpt, the library the Portfolio tool uses, but that takes seconds, so
the Home page does not solve it on load: the result lives in
assets/example_frontier.json. tests/test_example_market.py solves it again and
fails if the file no longer matches. To regenerate the file:

    python -m core.example_market

The cloud of random portfolios is cheap and seeded (mulberry32, seed 42, like
the test fixtures), so it is drawn on load and is identical on every run.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from core.constants import RISK_FREE_RATE

DATA_FILE = Path(__file__).resolve().parents[1] / "assets" / "example_frontier.json"

NAMES = ["A", "B", "C", "D", "E"]
COLORS = ["#2E6FC7", "#5B93E0", "#10B981", "#8DB8F2", "#F59E0B"]
MU = np.array([0.045, 0.070, 0.095, 0.125, 0.085])
SD = np.array([0.060, 0.120, 0.170, 0.240, 0.200])
CORR = np.array([
    [1.00, 0.30, 0.20, 0.10, 0.20],
    [0.30, 1.00, 0.50, 0.40, 0.30],
    [0.20, 0.50, 1.00, 0.60, 0.40],
    [0.10, 0.40, 0.60, 1.00, 0.50],
    [0.20, 0.30, 0.40, 0.50, 1.00],
])
COV = CORR * np.outer(SD, SD)


def _mulberry32(seed: int):
    """Small seeded PRNG (32-bit arithmetic), returns floats in [0, 1)."""
    a = seed & 0xFFFFFFFF

    def imul(x, y):
        return (x * y) & 0xFFFFFFFF

    def rand():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = imul(a ^ (a >> 15), 1 | a)
        t = ((t + imul(t ^ (t >> 7), 61 | t)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


def random_portfolios(count: int = 2500, seed: int = 42) -> list:
    """Random long-only portfolios as [volatility, return] pairs."""
    rand = _mulberry32(seed)
    points = []
    for k in range(count):
        # Every third draw is skewed towards concentrated portfolios so the
        # cloud reaches the edges of the feasible region.
        power = 4 if k % 3 == 0 else 1.2
        u = np.array([rand() ** power + 1e-9 for _ in range(len(MU))])
        w = u / u.sum()
        points.append([float(np.sqrt(w @ COV @ w)), float(w @ MU)])
    return points


def solve_example_frontier(points: int = 60) -> dict:
    """
    Solve the example market with PyPortfolioOpt (slow: seconds).

    Returns:
        Dict with the risk-free rate, the long-only efficient frontier as
        [volatility, return] pairs, and the Min Variance and Max Sharpe
        portfolios (weights in NAMES order, return, volatility, Sharpe).
    """
    from pypfopt import EfficientFrontier

    mu = pd.Series(MU, index=NAMES)
    cov = pd.DataFrame(COV, index=NAMES, columns=NAMES)

    def solved(method, **kwargs):
        ef = EfficientFrontier(mu, cov)
        getattr(ef, method)(**kwargs)
        weights = ef.clean_weights(cutoff=0, rounding=None)
        ret, vol, sharpe = ef.portfolio_performance(risk_free_rate=RISK_FREE_RATE)
        return {"weights": [float(weights[n]) for n in NAMES],
                "ret": float(ret), "vol": float(vol), "sharpe": float(sharpe)}

    min_variance = solved("min_volatility")
    max_sharpe = solved("max_sharpe", risk_free_rate=RISK_FREE_RATE)
    frontier = [[min_variance["vol"], min_variance["ret"]]]
    for target in np.linspace(min_variance["ret"], MU.max() - 1e-4, points)[1:]:
        p = solved("efficient_return", target_return=float(target))
        frontier.append([p["vol"], p["ret"]])

    return {"rf": RISK_FREE_RATE, "frontier": frontier,
            "min_variance": min_variance, "max_sharpe": max_sharpe}


def load_example_frontier() -> dict:
    """Everything Fig. 1 draws: the stored solution plus the assets and the cloud."""
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    data.update(names=NAMES, colors=COLORS, mu=MU.tolist(), sd=SD.tolist(),
                cloud=random_portfolios())
    return data


if __name__ == "__main__":
    DATA_FILE.write_text(json.dumps(solve_example_frontier(), indent=1) + "\n", encoding="utf-8")
    print("wrote", DATA_FILE)
