"""
Utilities package for the PortfolioLab Streamlit app.
"""

import logging

# Logging for the whole app, here because every page imports this package.
# It used to be set only in streamlit_app.py, so a process whose first visit
# was a subpage (a shared /Portfolio link after a reboot) logged nothing at
# INFO, and warnings lost their level and logger name (audit B3-19).
# basicConfig does nothing if logging is already configured (e.g. by pytest).
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
)

from .session_manager import (  # noqa: E402
    init_session_state,
    save_config,
    get_config,
    save_result,
    get_result,
    clear_results,
    should_show_results
)

from .optimizer_wrapper import run_optimization  # noqa: E402

__all__ = [
    'init_session_state',
    'save_config',
    'get_config',
    'save_result',
    'get_result',
    'clear_results',
    'should_show_results',
    'run_optimization'
]
