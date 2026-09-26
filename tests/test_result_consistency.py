"""
What the pages and the PDF show must describe the same run, correctly labeled.

Each test here pins a defect found by the 2026-09-26 audit (AUDITORIA.md):
a correlation heatmap that mislabeled its cells unless the tickers were typed
in alphabetical order, a PDF backtest on different rows than the web one, a
"$nan" share price, Black-Litterman text in Markowitz reports, and 0% bars
for assets without a view. All offline, on the mocked yfinance fixtures.
"""

import numpy as np
import pandas as pd
import pytest
from fpdf import FPDF
from pypfopt import risk_models

from utils.optimizer_wrapper import run_backtest, run_optimization
from utils.pdf_generator import generate_portfolio_pdf
from utils.visualizations import (
    create_correlation_heatmap,
    create_historical_performance_chart,
    create_returns_comparison,
)


def optimize(tickers, **kwargs):
    kwargs.setdefault("model_type", "Markowitz")
    kwargs.setdefault("obj_function", "Min Variance")
    result = run_optimization(tickers=tickers, portfolio_value=10000, **kwargs)
    assert result["success"], result.get("error")
    return result


@pytest.fixture
def pdf_text(monkeypatch):
    """Generate a report and return every string written into it."""
    def _generate(result):
        texts = []
        original_cell, original_multi_cell = FPDF.cell, FPDF.multi_cell

        def cell(self, *args, **kwargs):
            texts.append(str(args[2] if len(args) > 2 else kwargs.get("text", "")))
            return original_cell(self, *args, **kwargs)

        def multi_cell(self, *args, **kwargs):
            texts.append(str(args[2] if len(args) > 2 else kwargs.get("text", "")))
            return original_multi_cell(self, *args, **kwargs)

        monkeypatch.setattr(FPDF, "cell", cell)
        monkeypatch.setattr(FPDF, "multi_cell", multi_cell)
        generate_portfolio_pdf(result)
        monkeypatch.undo()
        return "\n".join(texts)
    return _generate


def test_covariance_matrix_follows_the_typed_ticker_order(synthetic_prices, mock_yfinance):
    """Prices download in alphabetical order; the heatmap labels follow the user's."""
    typed = ["MSFT", "GOOGL", "AAPL"]
    result = optimize(typed)

    assert result["covariance_tickers"] == typed
    expected = risk_models.CovarianceShrinkage(synthetic_prices[sorted(typed)]).ledoit_wolf()
    np.testing.assert_allclose(result["covariance_matrix"], expected.loc[typed, typed].values, rtol=1e-12)

    fig = create_correlation_heatmap(np.array(result["covariance_matrix"]), result["covariance_tickers"])
    assert list(fig.data[0].x) == typed


def test_estimates_use_the_dates_every_asset_has_a_price(synthetic_prices, mock_yfinance):
    """
    A late-listed asset must not have its missing years counted as zero
    returns (PyPortfolioOpt's Ledoit-Wolf zero-fills gaps). The run must equal
    raw PyPortfolioOpt on the complete rows only.
    """
    from pypfopt import EfficientFrontier

    synthetic_prices.iloc[:200, synthetic_prices.columns.get_loc("GOOGL")] = np.nan
    result = optimize(["AAPL", "GOOGL", "MSFT"])

    complete = synthetic_prices[["AAPL", "GOOGL", "MSFT"]].dropna()
    assert result["full_data_range"][0] == complete.index[0].strftime("%Y-%m-%d")

    S = risk_models.CovarianceShrinkage(complete).ledoit_wolf()
    np.testing.assert_allclose(result["covariance_matrix"], S.values, rtol=1e-12)

    ef = EfficientFrontier(pd.Series(result["posterior"])[S.index], S)
    ef.min_volatility()
    assert result["weights"] == ef.clean_weights()


def test_backtest_works_when_the_portfolio_holds_the_benchmark(mock_yfinance):
    """SPY can be one of the user's assets and the benchmark at once (it broke on 2026-09-26:
    the benchmark column was taken twice and both backtests failed)."""
    result = optimize(["AAPL", "MSFT", "SPY"])

    prices = pd.DataFrame.from_dict(result["prices_clean"], orient="index")
    prices.index = pd.to_datetime(prices.index)
    _, web = create_historical_performance_chart(
        weights=result["weights"], tickers=result["tickers"],
        portfolio_value=result["portfolio_value"], prices_data=prices, model_type="Markowitz",
    )
    pdf = run_backtest(result)

    assert web is not None and pdf is not None
    assert pdf["return"] == web.portfolio_metrics.annualized_return
    assert pdf["spy_return"] == web.benchmark_metrics.annualized_return


def test_web_and_pdf_backtest_the_same_rows(synthetic_prices, mock_yfinance):
    """A late-listed asset must not make the PDF backtest a longer period than the web."""
    synthetic_prices.iloc[:200, synthetic_prices.columns.get_loc("GOOGL")] = np.nan
    first_googl = synthetic_prices.index[200].strftime("%Y-%m-%d")
    result = optimize(["AAPL", "MSFT", "GOOGL"])

    assert result["backtest_range"][0] == first_googl
    assert result["data_notes"]["late_assets"] == [("GOOGL", first_googl)]

    prices = pd.DataFrame.from_dict(result["prices_clean"], orient="index")
    prices.index = pd.to_datetime(prices.index)
    _, web = create_historical_performance_chart(
        weights=result["weights"], tickers=result["tickers"],
        portfolio_value=result["portfolio_value"], initial_date=result["date_range"][0],
        prices_data=prices, model_type="Markowitz",
    )
    pdf = run_backtest(result, date_range=result["date_range"])

    assert (web.dates[0], web.dates[-1]) == tuple(result["backtest_range"])
    assert pdf["period"] == f"{web.dates[0]} to {web.dates[-1]}"
    for key, metric in [("return", "annualized_return"), ("volatility", "annualized_volatility"),
                        ("sharpe", "sharpe_ratio"), ("max_drawdown", "max_drawdown"),
                        ("sortino", "sortino_ratio"), ("calmar", "calmar_ratio")]:
        assert pdf[key] == getattr(web.portfolio_metrics, metric), key
        assert pdf[f"spy_{key}"] == getattr(web.benchmark_metrics, metric), key


def test_share_prices_skip_a_missing_last_close(synthetic_prices, mock_yfinance, pdf_text):
    """
    With crypto in the mix the last row can be a weekend, with no stock close.
    Shares are bought at the last close there is, and the PDF must say so, not "$nan".
    """
    previous_close = float(synthetic_prices["AAPL"].iloc[-2])
    synthetic_prices.iloc[-1, synthetic_prices.columns.get_loc("AAPL")] = np.nan
    result = optimize(["AAPL", "MSFT", "GOOGL"])

    assert result["latest_prices"]["AAPL"] == pytest.approx(previous_close)
    text = pdf_text(result)
    assert "$nan" not in text
    assert f"${previous_close:,.2f}" in text

    # Results saved before latest_prices existed: the PDF forward-fills itself
    del result["latest_prices"]
    text = pdf_text(result)
    assert "$nan" not in text
    assert f"${previous_close:,.2f}" in text


def test_markowitz_report_describes_markowitz(mock_yfinance, pdf_text):
    text = pdf_text(optimize(["AAPL", "MSFT", "GOOGL"]))

    assert "Mean-variance optimization (Markowitz)" in text
    assert "Black-Litterman" not in text
    assert "BL Portfolio" not in text


def test_black_litterman_report_describes_black_litterman(mock_yfinance, pdf_text, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda seconds: None)  # market-cap request pacing
    result = optimize(["AAPL", "MSFT", "GOOGL"], model_type="Black-Litterman",
                      obj_function="Max Sharpe", l2_gamma=1.0)
    text = pdf_text(result)

    assert "Black-Litterman model, following the PyPortfolioOpt cookbook" in text
    assert "gamma = 1.0" in text
    assert "Mean-variance" not in text


def test_assets_without_a_view_get_no_view_bar():
    """A missing bar, not a 0% one: 0% would read as a view that the asset returns nothing."""
    fig = create_returns_comparison(
        market_prior={"AAPL": 0.10, "MSFT": 0.08},
        posterior={"AAPL": 0.11, "MSFT": 0.085},
        views={"AAPL": 0.15},
    )
    views = next(trace for trace in fig.data if trace.name == "Your Views")
    assert views.y[0] == pytest.approx(15.0)
    assert views.y[1] is None
