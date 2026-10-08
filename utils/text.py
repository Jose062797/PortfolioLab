"""
Text helpers for what the pages show.
"""

import math
import re

# Characters that markdown (and Streamlit's renderer) can turn into
# formatting, links, images, math or HTML.
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>$~&])")


def escape_markdown(text) -> str:
    """
    Text typed by the user, shown literally inside st.markdown, st.warning
    and the like: no bold, links, images or formulas (audit B5-07).
    """
    return _MARKDOWN_SPECIAL.sub(r"\\\1", str(text))


def fmt_price(value) -> str:
    """
    A price with two decimals, or with four significant digits below 1.

    Two decimals turned prices under a cent (SHIB-USD) into 0.00 on the
    Stocks page, the allocation table and the PDF (audit F1-05).
    """
    value = float(value)
    if value == 0 or abs(value) >= 1:
        return f"{value:,.2f}"
    decimals = min(10, max(2, 3 - math.floor(math.log10(abs(value)))))
    return f"{value:,.{decimals}f}"
