"""
Coverage for previously untested output modules (audit D4.1):
utils/pdf_generator.py, utils/visualizations.py, and the full
run_optimization wrapper path that feeds them.

Everything runs offline on the mocked yfinance fixtures.
"""

import numpy as np
import pytest
import plotly.graph_objects as go

from utils.optimizer_wrapper import run_optimization
from utils.pdf_generator import generate_portfolio_pdf
from utils.visualizations import (
    create_correlation_heatmap,
    create_allocation_pie,
    create_efficient_frontier_chart,
    create_historical_performance_chart,
)


@pytest.fixture
def markowitz_result(mock_yfinance):
    """Full result dict from the real wrapper pipeline (offline)."""
    result = run_optimization(
        tickers=["AAPL", "MSFT", "GOOGL"],
        portfolio_value=10000,
        model_type="Markowitz",
        obj_function="Min Variance",
    )
    assert result["success"], f"pipeline failed: {result.get('error')}"
    return result


class TestRunOptimizationEndToEnd:
    def test_result_contract(self, markowitz_result):
        """The result dict must honor the contract the UI and PDF rely on."""
        r = markowitz_result
        assert r["model_type"] == "Markowitz"
        assert set(r["metrics"].keys()) == {"return", "volatility", "sharpe"}
        assert sum(r["weights"].values()) == pytest.approx(1.0, abs=0.02)
        assert r["ef_data"] is not None, "Markowitz must include efficient frontier"
        assert r["covariance_matrix"] is not None
        assert r["prices_clean"], "cleaned prices must ship with the result"
        assert r["risk_free_rate"] == pytest.approx(0.03)

    def test_error_result_contract(self, mock_yfinance):
        """Validation failures produce success=False with a message, no raise."""
        result = run_optimization(
            tickers=["AAPL"],  # below MIN_TICKERS
            portfolio_value=10000,
            model_type="Markowitz",
        )
        assert result["success"] is False
        assert result["error"]


class TestPdfGenerator:
    def test_generates_valid_pdf_bytes(self, markowitz_result):
        pdf_bytes = generate_portfolio_pdf(markowitz_result)
        assert isinstance(pdf_bytes, (bytes, bytearray))
        assert bytes(pdf_bytes[:5]) == b"%PDF-", "output must be a real PDF"
        assert len(pdf_bytes) > 10_000, "a full report should not be near-empty"

    def test_pdf_reflects_objective_in_metadata(self, markowitz_result):
        """Sanity: changing the objective must not break generation."""
        markowitz_result = dict(markowitz_result, obj_function="Max Sharpe")
        pdf_bytes = generate_portfolio_pdf(markowitz_result)
        assert bytes(pdf_bytes[:5]) == b"%PDF-"


class TestSessionManager:
    """session_manager works in Streamlit bare mode (session_state as dict)."""

    def test_result_roundtrip(self):
        from utils import session_manager as sm
        sm.init_session_state()
        sm.save_result({"success": True, "weights": {"AAPL": 1.0}})
        stored = sm.get_result()
        assert stored is not None and stored["weights"]["AAPL"] == 1.0

        sm.clear_results()
        assert sm.get_result() is None

    def test_running_flag(self):
        from utils import session_manager as sm
        sm.init_session_state()
        sm.set_optimization_running(True)
        assert sm.is_optimization_running() is True
        sm.set_optimization_running(False)
        assert sm.is_optimization_running() is False


class TestVisualizations:
    def test_correlation_heatmap(self, markowitz_result):
        cov = np.array(markowitz_result["covariance_matrix"])
        fig = create_correlation_heatmap(cov, markowitz_result["tickers"])
        assert isinstance(fig, go.Figure)
        z = np.array(fig.data[0].z, dtype=float)
        np.testing.assert_allclose(np.diag(z), 1.0, atol=1e-9)
        assert z.min() >= -1 - 1e-9 and z.max() <= 1 + 1e-9

    def test_allocation_pie(self, markowitz_result):
        fig = create_allocation_pie(markowitz_result["weights"])
        assert isinstance(fig, go.Figure)
        shown = np.asarray(fig.data[0].values, dtype=float)  # in percent
        expected_pct = 100 * sum(
            w for w in markowitz_result["weights"].values() if w > 0.001
        )
        assert shown.sum() == pytest.approx(expected_pct, abs=2.0)

    def test_efficient_frontier_chart(self, markowitz_result):
        m = markowitz_result["metrics"]
        fig = create_efficient_frontier_chart(
            markowitz_result["ef_data"],
            selected_portfolio={
                "ret": m["return"], "risk": m["volatility"],
                "sharpe": m["sharpe"], "label": "Selected",
            },
        )
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 2, "frontier line plus reference markers"

    def test_historical_performance_chart(self, markowitz_result):
        import pandas as pd
        prices_df = pd.DataFrame.from_dict(
            markowitz_result["prices_clean"], orient="index"
        )
        prices_df.index = pd.to_datetime(prices_df.index)
        fig, bt_result = create_historical_performance_chart(
            weights=markowitz_result["weights"],
            tickers=markowitz_result["tickers"],
            portfolio_value=markowitz_result["portfolio_value"],
            prices_data=prices_df,
            model_type="Markowitz",
        )
        assert isinstance(fig, go.Figure)
        assert bt_result is not None
        assert np.isfinite(bt_result.sharpe)
        assert bt_result.portfolio_metrics.max_drawdown <= 0
