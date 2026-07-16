"""Tests for utils.optimizer_wrapper — input validation."""

import numpy as np
import pytest

from utils.optimizer_wrapper import validate_inputs, find_highly_correlated_pairs


class TestValidateInputs:
    """Test the Streamlit input validator."""

    def test_valid_inputs(self):
        """Valid inputs should pass."""
        is_valid, error = validate_inputs(
            tickers=["AAPL", "MSFT"],
            portfolio_value=10000,
        )
        assert is_valid is True
        assert error is None

    def test_too_few_tickers(self):
        """Less than MIN_TICKERS should fail."""
        is_valid, error = validate_inputs(
            tickers=["AAPL"],
            portfolio_value=10000,
        )
        assert is_valid is False
        assert "at least" in error.lower()

    def test_too_many_tickers(self):
        """More than MAX_TICKERS should fail."""
        tickers = [f"T{i}" for i in range(25)]
        is_valid, error = validate_inputs(
            tickers=tickers,
            portfolio_value=10000,
        )
        assert is_valid is False
        assert "Maximum" in error or "maximum" in error.lower()

    def test_duplicate_tickers(self):
        """Duplicate tickers should fail."""
        is_valid, error = validate_inputs(
            tickers=["AAPL", "MSFT", "AAPL"],
            portfolio_value=10000,
        )
        assert is_valid is False
        assert "Duplicate" in error

    def test_portfolio_too_small(self):
        """Portfolio below MIN_PORTFOLIO_VALUE should fail."""
        is_valid, error = validate_inputs(
            tickers=["AAPL", "MSFT"],
            portfolio_value=1,
        )
        assert is_valid is False
        assert "at least" in error.lower()

    def test_portfolio_too_large(self):
        """Portfolio above MAX_PORTFOLIO_VALUE should fail."""
        is_valid, error = validate_inputs(
            tickers=["AAPL", "MSFT"],
            portfolio_value=2e12,
        )
        assert is_valid is False
        assert "exceed" in error.lower()

    def test_invalid_date_range(self):
        """Start >= end should fail."""
        from datetime import datetime
        is_valid, error = validate_inputs(
            tickers=["AAPL", "MSFT"],
            portfolio_value=10000,
            date_range=(datetime(2024, 6, 1), datetime(2024, 1, 1)),
        )
        assert is_valid is False
        assert "before" in error.lower()

    def test_invalid_ticker_format_rejected(self):
        """Arbitrary text must never flow past validation (audit D7.1)."""
        for bad in ["<SCRIPT>", "AA PL", "TICKER!", "A" * 16, "😀"]:
            is_valid, error = validate_inputs(
                tickers=["AAPL", bad],
                portfolio_value=10000,
            )
            assert is_valid is False, f"{bad!r} should be rejected"
            assert "Invalid ticker" in error

    def test_exotic_but_valid_symbols_accepted(self):
        """Yahoo's real symbol zoo must keep working."""
        is_valid, error = validate_inputs(
            tickers=["BRK-B", "BF.B", "^GSPC", "BTC-USD", "EURUSD=X"],
            portfolio_value=10000,
        )
        assert is_valid is True, error

    def test_black_litterman_rejects_forex(self):
        """BL needs market caps; forex pairs have none (audit follow-up)."""
        is_valid, error = validate_inputs(
            tickers=["AAPL", "EURUSD=X"],
            portfolio_value=10000,
            model_type="Black-Litterman",
        )
        assert is_valid is False
        assert "EURUSD=X" in error and "Markowitz" in error

    def test_markowitz_allows_forex(self):
        """Markowitz remains available for forex portfolios."""
        is_valid, error = validate_inputs(
            tickers=["AAPL", "EURUSD=X"],
            portfolio_value=10000,
            model_type="Markowitz",
        )
        assert is_valid is True, error

    def test_view_for_unknown_ticker(self):
        """View for non-existent ticker should fail."""
        is_valid, error = validate_inputs(
            tickers=["AAPL", "MSFT"],
            portfolio_value=10000,
            views={"TSLA": {"expected": 0.15}},
        )
        assert is_valid is False
        assert "TSLA" in error

    def test_unrealistic_view(self):
        """View > 200% should fail."""
        is_valid, error = validate_inputs(
            tickers=["AAPL", "MSFT"],
            portfolio_value=10000,
            views={"AAPL": {"expected": 5.0}},
        )
        assert is_valid is False
        assert "unrealistic" in error.lower()


class TestFindHighlyCorrelatedPairs:
    """Overlap detector for redundant holdings (ETF alongside constituents)."""

    def _cov_from_corr(self, corr, vols):
        corr = np.asarray(corr, dtype=float)
        vols = np.asarray(vols, dtype=float)
        return (corr * np.outer(vols, vols)).tolist()

    def test_detects_overlapping_pair(self):
        cov = self._cov_from_corr(
            [[1.00, 0.98, 0.30],
             [0.98, 1.00, 0.25],
             [0.30, 0.25, 1.00]],
            [0.25, 0.22, 0.18],
        )
        pairs = find_highly_correlated_pairs(cov, ["AAPL", "QQQ", "KO"])
        assert len(pairs) == 1
        a, b, c = pairs[0]
        assert {a, b} == {"AAPL", "QQQ"}
        assert c == pytest.approx(0.98, abs=1e-9)

    def test_no_pairs_below_threshold(self):
        cov = self._cov_from_corr(
            [[1.0, 0.6], [0.6, 1.0]], [0.2, 0.3]
        )
        assert find_highly_correlated_pairs(cov, ["A", "B"]) == []

    def test_garbage_input_returns_empty(self):
        assert find_highly_correlated_pairs(None, ["A"]) == []
        assert find_highly_correlated_pairs([[1, 2], [3]], ["A", "B"]) == []
        assert find_highly_correlated_pairs([[0.0]], ["A"]) == []
