"""
SSL Certificate Fix for non-ASCII paths.

curl_cffi (yfinance dependency) cannot read cacert.pem from paths
with non-ASCII characters (e.g. Spanish accents in OneDrive paths).
When certifi's bundle sits on such a path, this module keeps a copy at a
safe ASCII path (%LOCALAPPDATA%\\ssl) and points CURL_CA_BUNDLE at it.
Anywhere else (ASCII paths, Linux/Streamlit Cloud) it does nothing.

Usage:
    import utils.ssl_fix  # auto-applies on import (module-level)
"""

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def apply_ssl_fix() -> None:
    """Copy certifi's bundle to an ASCII path, only when curl needs it."""
    try:
        import certifi
        source = Path(certifi.where())
    except Exception as e:
        logger.warning("SSL fix skipped: certifi not available (%s)", e)
        return

    # An ASCII path works as is. Until 2026-10-08 the copy was made on every
    # machine and never refreshed, so a certifi upgrade left a stale bundle,
    # and on Linux (no LOCALAPPDATA) it landed in a relative ./ssl folder.
    if str(source).isascii():
        return
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        return

    ssl_cert = Path(local_appdata) / "ssl" / "cacert.pem"
    try:
        # Refresh the copy whenever certifi's bundle changes
        if not ssl_cert.exists() or ssl_cert.read_bytes() != source.read_bytes():
            ssl_cert.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, ssl_cert)
    except Exception as e:
        logger.warning("SSL fix: could not copy the CA bundle to %s: %s", ssl_cert, e)
        return

    os.environ["CURL_CA_BUNDLE"] = str(ssl_cert)


# Auto-apply on import
apply_ssl_fix()
