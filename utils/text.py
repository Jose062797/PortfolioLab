"""
Text helpers for what the pages show.
"""

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
