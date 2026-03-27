"""
SSL Certificate Fix for non-ASCII paths.

curl_cffi (yfinance dependency) cannot read cacert.pem from paths
with non-ASCII characters (e.g. Spanish accents in OneDrive paths).
This module copies the certificate to a safe ASCII path once,
and sets the CURL_CA_BUNDLE environment variable.

Usage:
    import utils.ssl_fix  # auto-applies on import (module-level)
"""

import os
import shutil
from pathlib import Path


def apply_ssl_fix() -> None:
    """Copy cacert.pem to a safe ASCII path if needed."""
    ssl_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "ssl"
    ssl_cert = ssl_dir / "cacert.pem"

    if not ssl_cert.exists():
        try:
            import certifi
            ssl_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(certifi.where(), ssl_cert)
        except Exception:
            pass

    if ssl_cert.exists():
        os.environ["CURL_CA_BUNDLE"] = str(ssl_cert)


# Auto-apply on import
apply_ssl_fix()
