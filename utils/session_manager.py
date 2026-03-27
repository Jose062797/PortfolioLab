"""
Session State Management for Black-Litterman Streamlit App

This module handles all Streamlit session state management to ensure
consistent state across page navigation and user interactions.
"""

import streamlit as st
from typing import Dict, List, Optional, Any

from core.constants import MIN_WEIGHT_THRESHOLD


def init_session_state() -> None:
    """
    Initialize all required session state variables.

    This should be called at the start of each page to ensure
    all necessary session variables exist.
    """
    # Optimization results
    if 'optimization_result' not in st.session_state:
        st.session_state.optimization_result = None

    # Portfolio configuration
    if 'portfolio_config' not in st.session_state:
        st.session_state.portfolio_config = {
            'tickers': [],
            'portfolio_value': 10000,
            'date_range': None,
            'views': {}
        }

    # UI state flags
    if 'show_results' not in st.session_state:
        st.session_state.show_results = False

    if 'optimization_running' not in st.session_state:
        st.session_state.optimization_running = False

    # History tracking
    if 'optimization_history' not in st.session_state:
        st.session_state.optimization_history = []

    # Current page tracking
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'home'


def save_config(
    tickers: List[str],
    portfolio_value: float,
    date_range: Optional[tuple] = None,
    views: Optional[Dict[str, Dict[str, float]]] = None
) -> None:
    """
    Save portfolio configuration to session state.

    Args:
        tickers: List of stock ticker symbols
        portfolio_value: Total portfolio value in USD
        date_range: Optional tuple of (start_date, end_date)
        views: Optional dict of investment views
               Format: {'TICKER': {'expected': 0.15, 'lower': 0.10, 'upper': 0.20}}
    """
    st.session_state.portfolio_config = {
        'tickers': tickers,
        'portfolio_value': portfolio_value,
        'date_range': date_range,
        'views': views if views is not None else {}
    }


def get_config() -> Dict[str, Any]:
    """
    Get current portfolio configuration from session state.

    Returns:
        Dictionary containing current portfolio configuration
    """
    if 'portfolio_config' not in st.session_state:
        init_session_state()

    return st.session_state.portfolio_config


def save_result(result: Dict[str, Any]) -> None:
    """
    Save optimization result to session state and mark results as ready to display.

    Args:
        result: Dictionary containing optimization results with keys:
                - success: bool
                - metrics: dict
                - weights: dict
                - allocation: dict
                - etc.
    """
    st.session_state.optimization_result = result
    st.session_state.show_results = True

    # Add to history if successful
    if result.get('success', False):
        add_to_history(result)


def get_result() -> Optional[Dict[str, Any]]:
    """
    Get current optimization result from session state.

    Returns:
        Optimization result dictionary or None if no results available
    """
    return st.session_state.get('optimization_result')


def clear_results() -> None:
    """
    Clear optimization results from session state.
    """
    st.session_state.optimization_result = None
    st.session_state.show_results = False


def should_show_results() -> bool:
    """
    Check if results should be displayed.

    Returns:
        True if results are ready and should be shown, False otherwise
    """
    return st.session_state.get('show_results', False)


def set_optimization_running(is_running: bool) -> None:
    """
    Set the optimization running state.

    Args:
        is_running: True if optimization is in progress, False otherwise
    """
    st.session_state.optimization_running = is_running


def is_optimization_running() -> bool:
    """
    Check if optimization is currently running.

    Returns:
        True if optimization is in progress, False otherwise
    """
    return st.session_state.get('optimization_running', False)


def add_to_history(result: Dict[str, Any]) -> None:
    """
    Add optimization result to history.

    Args:
        result: Optimization result dictionary
    """
    if 'optimization_history' not in st.session_state:
        st.session_state.optimization_history = []

    # Add timestamp if not present
    from datetime import datetime
    if 'timestamp' not in result:
        result['timestamp'] = datetime.now().isoformat()

    # Store lightweight copy in history (exclude large price data to save memory)
    history_entry = {k: v for k, v in result.items() if k != 'prices_clean'}
    st.session_state.optimization_history.append(history_entry)

    # Keep last 10 results
    if len(st.session_state.optimization_history) > 10:
        st.session_state.optimization_history.pop(0)


def get_history() -> List[Dict[str, Any]]:
    """
    Get optimization history.

    Returns:
        List of optimization result dictionaries, newest first
    """
    if 'optimization_history' not in st.session_state:
        return []

    return list(reversed(st.session_state.optimization_history))


def clear_history() -> None:
    """
    Clear all optimization history.
    """
    st.session_state.optimization_history = []


def set_current_page(page_name: str) -> None:
    """
    Set the current page name.

    Args:
        page_name: Name of the current page
    """
    st.session_state.current_page = page_name


def get_current_page() -> str:
    """
    Get the current page name.

    Returns:
        Current page name
    """
    return st.session_state.get('current_page', 'home')


def reset_session() -> None:
    """
    Reset all session state to initial values.

    WARNING: This will clear all user data and results.
    """
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    init_session_state()


# Convenience functions for common operations

def has_unsaved_changes() -> bool:
    """
    Check if there are unsaved changes in the current configuration.

    Returns:
        True if configuration differs from last saved result, False otherwise
    """
    config = get_config()
    result = get_result()

    if result is None:
        return len(config.get('tickers', [])) > 0

    # Compare tickers
    if set(config.get('tickers', [])) != set(result.get('tickers', [])):
        return True

    # Compare portfolio value
    if abs(config.get('portfolio_value', 0) - result.get('portfolio_value', 0)) > 0.01:
        return True

    # Compare views
    if config.get('views', {}) != result.get('viewdict', {}):
        return True

    return False


def get_summary_stats() -> Dict[str, Any]:
    """
    Get summary statistics from current results.

    Returns:
        Dictionary with summary statistics or empty dict if no results
    """
    result = get_result()

    if result is None or not result.get('success', False):
        return {}

    return {
        'expected_return': result.get('metrics', {}).get('return', 0),
        'volatility': result.get('metrics', {}).get('volatility', 0),
        'sharpe_ratio': result.get('metrics', {}).get('sharpe', 0),
        'num_assets': len([w for w in result.get('weights', {}).values() if w > MIN_WEIGHT_THRESHOLD]),
        'num_positions': len(result.get('allocation', {})),
    }
