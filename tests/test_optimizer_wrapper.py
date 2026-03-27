"""Tests for utils.optimizer_wrapper — input validation."""

import pytest

from utils.optimizer_wrapper import validate_inputs


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
