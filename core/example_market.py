"""
Example data for the Home page: five made-up assets and one made-up stock.

Nothing here is market data, and the Home page says so ("Example data").
What IS real is the code that turns it into pictures: the Home page draws
the same charts the tools draw, with the same functions.

- The Portfolio example is a Markowitz run with the objective "Maximise
  Return for a Given Risk" at a 14% target volatility (L2 gamma 0, the
  Markowitz default), solved by the engine itself:
  core.opt_engine.calculate_efficient_frontier and optimize_portfolio. The
  expected returns and covariances are set by hand below, where a real run
  estimates them from prices. That objective puts the chosen portfolio at its
  own point on the frontier, apart from the Max Sharpe and Min Variance
  markers. Fig. 1 is create_efficient_frontier_chart on that result, the
  Portfolio card shows create_allocation_pie of its weights, and the parity
  table compares them with PyPortfolioOpt called directly.
- The Stocks example is one year of daily prices and volumes (a seeded
  random walk) for create_price_chart, the Stocks page's own chart, in the
  page's default view (1Y, Line).

Solving the frontier takes seconds, so the Home page does not solve it on
load: the results live in assets/example_frontier.json, and
tests/test_example_market.py solves everything again and fails if the file no
longer matches. To regenerate the file:

    python -m core.example_market
"""

import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

from core.constants import RISK_FREE_RATE

DATA_FILE = Path(__file__).resolve().parents[1] / "assets" / "example_frontier.json"

NAMES = ["A", "B", "C", "D", "E"]
MU = np.array([0.050, 0.070, 0.095, 0.125, 0.085])
SD = np.array([0.090, 0.120, 0.170, 0.240, 0.200])
CORR = np.array([
    [1.00, 0.30, 0.20, 0.10, 0.20],
    [0.30, 1.00, 0.50, 0.40, 0.30],
    [0.20, 0.50, 1.00, 0.60, 0.40],
    [0.10, 0.40, 0.60, 1.00, 0.50],
    [0.20, 0.30, 0.40, 0.50, 1.00],
])
COV = CORR * np.outer(SD, SD)
OBJECTIVE = "Maximise Return for a Given Risk"
TARGET_VOLATILITY = 0.14


def example_inputs() -> tuple:
    """Expected returns and covariance, shaped like the engine's inputs."""
    return (pd.Series(MU, index=NAMES),
            pd.DataFrame(COV, index=NAMES, columns=NAMES))


def _plain(value):
    """numpy scalars and containers to plain Python, for JSON."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def solve_example() -> dict:
    """
    Run the engine on the example assets, plus PyPortfolioOpt directly.

    Returns:
        Dict with "ef_data" (calculate_efficient_frontier), "portfolio"
        (optimize_portfolio: weights and its expected return, volatility and
        Sharpe ratio), "reference" (the same from PyPortfolioOpt's own
        EfficientFrontier.efficient_risk) and the PyPortfolioOpt version used.
    """
    import pypfopt
    from pypfopt import EfficientFrontier

    from core.opt_engine import calculate_efficient_frontier, optimize_portfolio

    mu, cov = example_inputs()
    ef_data = calculate_efficient_frontier(mu, cov)
    weights, perf = optimize_portfolio(mu, cov, obj_function=OBJECTIVE,
                                       target_volatility=TARGET_VOLATILITY, l2_gamma=0.0)

    ef = EfficientFrontier(mu, cov)
    ef.efficient_risk(target_volatility=TARGET_VOLATILITY)
    ref_weights = ef.clean_weights()
    ref_ret, ref_vol, ref_sharpe = ef.portfolio_performance(risk_free_rate=RISK_FREE_RATE)

    return _plain({
        "objective": OBJECTIVE,
        "target_volatility": TARGET_VOLATILITY,
        "rf": RISK_FREE_RATE,
        "pypfopt_version": pypfopt.__version__,
        "ef_data": ef_data,
        "portfolio": {"weights": dict(weights), "return": perf["expected_return"],
                      "volatility": perf["volatility"], "sharpe": perf["sharpe_ratio"]},
        "reference": {"weights": dict(ref_weights), "return": ref_ret,
                      "volatility": ref_vol, "sharpe": ref_sharpe},
    })


def load_example() -> dict:
    """The stored engine results (see solve_example)."""
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def example_ohlcv(days: int = 252, seed: int = 11) -> pd.DataFrame:
    """One year of made-up daily prices and volumes for the Stocks card."""
    rng = random.Random(seed)
    index = pd.bdate_range(end="2026-06-30", periods=days)
    rows, close = [], 100.0
    for _ in range(days):
        open_ = close * (1 + rng.gauss(0, 0.004))
        close = open_ * (1 + rng.gauss(0.0006, 0.013))
        high = max(open_, close) * (1 + abs(rng.gauss(0, 0.004)))
        low = min(open_, close) * (1 - abs(rng.gauss(0, 0.004)))
        volume = int(rng.lognormvariate(16.5, 0.35))
        rows.append((open_, high, low, close, volume))
    return pd.DataFrame(rows, index=index, columns=["Open", "High", "Low", "Close", "Volume"])


if __name__ == "__main__":
    DATA_FILE.write_text(json.dumps(solve_example(), indent=1) + "\n", encoding="utf-8")
    print("wrote", DATA_FILE)
