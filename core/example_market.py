"""
Examples for the Home page.

- EXAMPLE_PORTFOLIOS: real tickers and a goal. Each Home card links to
  ./Portfolio?example=<key>, which fills in the Portfolio form
  (pages/2_Portfolio.py); the user presses Run and the result is computed
  on live data like any other run. Checked on live data on 2026-09-26: all
  three run, and each goal gives a mix of assets, not a single one.
- The Portfolio card's picture: five made-up assets, A to E. Nothing here is
  market data, and the Home page labels it "Example". What IS real is the
  code that turns it into a picture: a Markowitz run with the objective
  "Maximise Return for a Given Risk" at a 14% target volatility (L2 gamma 0,
  the Markowitz default), solved by the engine itself
  (core.opt_engine.optimize_portfolio), and drawn by create_allocation_pie,
  the Portfolio page's own chart. The expected returns and covariances are
  set by hand below, where a real run estimates them from prices.
- The Stocks card's picture: one year of daily prices and volumes (a seeded
  random walk) for create_price_chart, the Stocks page's own chart, in the
  page's default view (1Y, Line).

The solved example lives in assets/example_portfolio.json, so the Home page
does not load the optimizer; tests/test_example_market.py solves it again and
fails if the file no longer matches. To regenerate the file:

    python -m core.example_market
"""

import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

from core.constants import RISK_FREE_RATE

# Keys are the ?example= values; "objective" is the engine's name
# (core.constants.OBJECTIVE_LABELS has the one users see). All three use
# Markowitz: Black-Litterman also needs market capitalizations, which Yahoo
# rate-limits on shared cloud servers, and an example should just work.
EXAMPLE_PORTFOLIOS = {
    "big-tech": {
        "title": "Big Tech",
        "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
        "objective": "Max Sharpe",
    },
    "dividends": {
        "title": "Dividend stocks",
        "tickers": ["KO", "PEP", "JNJ", "PG", "XOM"],
        "objective": "Min Variance",
    },
    "stocks-bonds-gold": {
        "title": "Stocks, bonds and gold",
        "tickers": ["VTI", "AGG", "GLD"],
        "objective": "Maximise Return for a Given Risk",
        "target_volatility": 0.10,
        # CAPM measures each asset against SPY, which leaves gold (beta near
        # zero) with almost no expected return and no weight; the historical
        # mean is the page's own advice for bonds and commodities.
        "returns_estimator": "historical",
    },
}

DATA_FILE = Path(__file__).resolve().parents[1] / "assets" / "example_portfolio.json"

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
    Run the engine on the made-up assets.

    Returns:
        Dict with the objective, its target volatility, the risk-free rate and
        "portfolio" (optimize_portfolio: weights and their expected return,
        volatility and Sharpe ratio).
    """
    from core.opt_engine import optimize_portfolio

    mu, cov = example_inputs()
    weights, perf = optimize_portfolio(mu, cov, obj_function=OBJECTIVE,
                                       target_volatility=TARGET_VOLATILITY, l2_gamma=0.0)
    return _plain({
        "objective": OBJECTIVE,
        "target_volatility": TARGET_VOLATILITY,
        "rf": RISK_FREE_RATE,
        "portfolio": {"weights": dict(weights), "return": perf["expected_return"],
                      "volatility": perf["volatility"], "sharpe": perf["sharpe_ratio"]},
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
