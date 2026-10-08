"""
The PDF report (audit 2026-10-08, package B).

It must say the same things as the web, in the web's words; a missing or
failed section leaves a line instead of vanishing or sinking the download;
and its charts must be right when several visitors download at once.
"""

import re
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest
from fpdf import FPDF

from utils.optimizer_wrapper import run_optimization
from utils.pdf_generator import generate_portfolio_pdf


@pytest.fixture
def markowitz_result(mock_yfinance):
    result = run_optimization(["AAPL", "MSFT", "GOOGL"], 10000, model_type="Markowitz",
                              obj_function="Min Variance")
    assert result["success"], result.get("error")
    from utils.optimizer_wrapper import run_backtest
    result["historical_data"] = run_backtest(result)
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
        pdf = generate_portfolio_pdf(result)
        monkeypatch.setattr(FPDF, "cell", original_cell)
        monkeypatch.setattr(FPDF, "multi_cell", original_multi_cell)
        assert bytes(pdf[:5]) == b"%PDF-"
        return "\n".join(texts)
    return _generate


class TestWording:

    def test_a_target_prints_as_typed(self, markowitz_result, pdf_text):
        """`:.0%` turned a 12.5% limit into "at most 12%" next to a breakdown
        that said 12.5% (audit F1-01)."""
        text = pdf_text(dict(markowitz_result, obj_function="Maximise Return for a Given Risk",
                             target_volatility=0.125))

        assert "volatility of at most 12.5%" in text
        assert "at most 12%" not in text and "at most 13%" not in text

    def test_black_litterman_without_l2_says_so(self, markowitz_result, pdf_text):
        text = pdf_text(dict(markowitz_result, model_type="Black-Litterman", l2_gamma=0.0,
                             obj_function="Max Sharpe"))

        assert "with no L2 penalty (gamma = 0)" in text
        assert "an L2 penalty (gamma = 0.0)" not in text

    def test_the_web_vocabulary(self, markowitz_result, pdf_text):
        text = pdf_text(markowitz_result)

        for word in ("Budget:", "Cash left over:", "Run on:", "Expected returns:", "Sharpe Ratio"):
            assert word in text, word
        for old in ("Portfolio Value", "Total Value", "Cash Remaining", "Optimization Date",
                    "Ex-Ante", "Ex-Post"):
            assert old not in text, old

    @pytest.mark.parametrize("portfolio_return, spy_return, wording", [
        (12.0, 12.5, "returned 12.00% a year, roughly matching"),
        (15.0, 10.0, "outperformed SPY by 5.00 percentage points a year"),
        (6.0, 10.0, "underperformed SPY by 4.00 percentage points a year"),
    ])
    def test_backtest_returns_read_as_annual(self, portfolio_return, spy_return, wording, monkeypatch):
        """Annualized returns read as totals without "a year" (audit F1-17),
        in each of the comparison's three wordings."""
        from core.pdf_shared import add_historical_metrics

        texts = []
        original = FPDF.multi_cell

        def multi_cell(self, *args, **kwargs):
            texts.append(str(args[2] if len(args) > 2 else kwargs.get("text", "")))
            return original(self, *args, **kwargs)

        monkeypatch.setattr(FPDF, "multi_cell", multi_cell)
        pdf = FPDF()
        pdf.add_page()
        metrics = {"return": portfolio_return, "volatility": 15.0, "sharpe": 0.6,
                   "max_drawdown": -20.0, "sortino": 0.8, "calmar": 0.5,
                   "spy_return": spy_return, "spy_volatility": 15.0, "spy_sharpe": 0.6,
                   "spy_max_drawdown": -20.0, "spy_sortino": 0.8, "spy_calmar": 0.5}
        add_historical_metrics(pdf, metrics, "Markowitz")

        comparison = next(t for t in texts if "The portfolio" in t)
        assert wording in comparison


class TestMissingSections:

    def test_a_missing_backtest_is_said_and_its_period_not_printed(self, markowitz_result, pdf_text):
        result = dict(markowitz_result, historical_data=None)
        assert result["backtest_range"], "the run has a backtest period to (not) print"
        text = pdf_text(result)

        assert "Historical performance: not available for this run" in text
        assert "not available for this run" in text.split("Backtest period:")[1]
        # Neither the cover's dated line nor the breakdown's
        assert not re.search(r"Backtest period: \d", text)
        assert "(days with a price for every asset and SPY)" not in text

    def test_a_failed_chart_leaves_a_line_not_a_failed_download(self, markowitz_result, pdf_text, monkeypatch):
        import utils.pdf_generator as generator

        def _broken(*args, **kwargs):
            raise RuntimeError("chart failed")

        monkeypatch.setattr(generator, "create_allocation_chart", _broken)
        text = pdf_text(markowitz_result)

        assert "The allocation chart could not be drawn for this run" in text
        assert "Detailed Breakdown" in text, "the rest of the report is still there"

    def test_backtests_of_20_days_reach_the_pdf(self, synthetic_prices):
        """The PDF's backtest needed 100 rows and the web's 20: a run of 20-99
        common days had a web backtest and none in the PDF (audit B3-06)."""
        from core.backtest import run_backtest

        result = run_backtest(synthetic_prices.head(60), {"AAPL": 0.5, "MSFT": 0.5},
                              ["AAPL", "MSFT"], 10000)
        assert result is not None


class TestChartsAcrossThreads:

    def test_no_pyplot_state(self):
        import core.pdf_shared as pdf_shared
        assert not hasattr(pdf_shared, "plt"), "pyplot's current figure is shared by every thread"

    def test_charts_built_at_once_equal_charts_built_alone(self):
        """The PDF is built on a worker thread per download. With pyplot,
        plt.tight_layout() acted on whichever figure was current: 96 of 96
        charts built in 8 threads came out with another size (audit B4-01)."""
        from core import pdf_shared

        rng = np.random.default_rng(0)
        inputs = []
        for n in (3, 5, 8):
            w = rng.random(n)
            a = rng.normal(size=(n, n))
            tickers = [f"T{n}_{i}" for i in range(n)]
            inputs.append(({t: float(x) for t, x in zip(tickers, w / w.sum())},
                           a @ a.T + n * np.eye(n), tickers))

        def build(i):
            weights, cov, tickers = inputs[i]
            return (pdf_shared.create_allocation_chart(weights),
                    pdf_shared.create_correlation_heatmap(cov, tickers))

        alone = [build(i) for i in range(len(inputs))]
        with ThreadPoolExecutor(max_workers=6) as pool:
            together = list(pool.map(build, [i % len(inputs) for i in range(18)]))

        assert all(got == alone[i % len(inputs)] for i, got in enumerate(together))
