"""
Session state for the Portfolio page: the latest optimization result.

Results live only in st.session_state (no disk), one per browser session.
Until 2026-10-08 this module also kept a history of the last ten results,
a saved form configuration and page/progress flags that nothing read: up to
ten extra result copies per visitor's memory (audit B8-01, B4-02).
"""

from typing import Any, Dict, Optional

import streamlit as st


def init_session_state() -> None:
    """Create the result slot, once per session."""
    if 'optimization_result' not in st.session_state:
        st.session_state.optimization_result = None


def save_result(result: Dict[str, Any]) -> None:
    """Keep a run's result for the results panel."""
    st.session_state.optimization_result = result


def get_result() -> Optional[Dict[str, Any]]:
    """The latest result, or None."""
    return st.session_state.get('optimization_result')


def clear_results() -> None:
    """Forget the latest result (a failed run must not show the previous one)."""
    st.session_state.optimization_result = None
