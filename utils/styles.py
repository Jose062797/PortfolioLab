"""
Shared Design System for PortfolioLab Platform

Modern design: clean, bold, no sidebar.
Top navigation bar, navy and brand-blue accents shared with the landing page
(docs/index.html), DM Mono for figures, generous whitespace.

MAINTENANCE MAP — Streamlit-internal selectors this module overrides
(these are the ONLY parts that can break when Streamlit updates; audit
them first after any `streamlit` version bump):

  - inject_critical_css():
      header[data-testid="stHeader"], [data-testid="stSidebar"],
      [data-testid="collapsedControl"], [data-testid="stToolbar"],
      section[data-testid="stSidebarNav"] — hide Streamlit chrome/sidebar.
      [data-testid="stAppViewContainer"] / [data-testid="stMain"] /
      .block-container — full-width breakout (max-width: none, negative
      margins, 3rem side padding, 30px top gap).
  - get_shared_css():
      [data-testid="stMetric*"] (metric cards); tabs, which Streamlit 1.59
      renders with react-aria ([role="tablist"], [role="tab"][aria-selected],
      label in a <p>; the older data-baseweb="tab" selectors match nothing);
      button labels (a <p> nested in divs inside the button, reached by the
      global `p, li, div, label` color rule unless overridden);
      [data-testid="stHeaderActionElements"] (heading link icons, hidden in
      designed blocks); the PWA helper iframe
      ([data-testid="stElementContainer"][height="1px"]); .stPlotlyChart
      (touch-action); plus the same .block-container overrides for pages
      (the mobile one must match the specificity of inject_critical_css()).
  - Everything prefixed `bl-` (navbar, band, tool cards, steps, facts,
      footer) is OUR namespace and does not depend on Streamlit internals.

Split decision (audit D8.1, 2026-07): kept as one module. The CSS is a
single coherent design system injected as one <style> block; splitting
into files would not reduce the Streamlit-version coupling (the risk
lives in the selectors above, not in file size) and would add import
ordering pitfalls between critical and shared CSS.
"""

import streamlit as st


def get_shared_css() -> str:
    """
    Return the complete shared CSS for the application.

    Includes:
    - Google Fonts (Inter for text, DM Sans for headings, DM Mono for figures)
    - Design tokens (blue palette matching PortfolioLab logo)
    - Streamlit chrome hiding + sidebar hiding
    - Top navigation bar
    - Modern typography, cards, buttons
    - Hero band, tool cards, method steps and verification facts
    """
    return """
<style>
    /* ===== Google Fonts ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=DM+Sans:wght@400;500;700&family=DM+Mono:wght@400;500&display=swap');

    /* ===== Design Tokens ===== */
    :root {
        --color-primary: #0A1628;
        --color-accent: #2E6FC7;
        --color-accent-hover: #1E5AB3;
        --color-accent-light: rgba(46, 111, 199, 0.1);
        --color-success: #10B981;
        --color-success-light: rgba(16, 185, 129, 0.1);
        --color-warning: #F59E0B;
        --color-warning-light: rgba(245, 158, 11, 0.1);
        --color-error: #EF4444;
        --color-error-light: rgba(239, 68, 68, 0.1);
        --color-bg: #F8FAFC;
        --color-surface: #FFFFFF;
        --color-border: rgba(226, 232, 240, 0.8);
        --color-border-light: rgba(241, 245, 249, 0.8);
        --color-text: #334155;
        --color-text-secondary: #64748B;
        --color-text-muted: #94A3B8;
        --color-sky: #8DB8F2;
        --color-surface-2: #EEF3FA;
        --color-line: rgba(10, 22, 40, 0.10);
        --color-line-strong: rgba(10, 22, 40, 0.18);
        --on-dark-2: #A3B4CC;
        --on-dark-line: rgba(232, 238, 248, 0.12);

        --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        --font-display: 'DM Sans', 'Inter', sans-serif;
        --font-mono: 'DM Mono', ui-monospace, 'SFMono-Regular', Consolas, monospace;

        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --radius-xl: 24px;
        --radius-full: 9999px;

        --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.05);
        --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        --shadow-glow: 0 0 20px rgba(46, 111, 199, 0.25);
        --shadow-card: 0 1px 2px rgba(10, 22, 40, 0.06), 0 10px 28px rgba(10, 22, 40, 0.07);

        --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
        --transition-base: 250ms cubic-bezier(0.4, 0, 0.2, 1);
        --transition-slow: 350ms cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* ===== Hide ALL Streamlit Chrome ===== */
    #MainMenu {display: none !important;}
    footer {display: none !important;}
    header[data-testid="stHeader"] {display: none !important;}
    header {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}

    /* ===== HIDE SIDEBAR COMPLETELY ===== */
    [data-testid="stSidebar"] {display: none !important;}
    [data-testid="stSidebarNav"] {display: none !important;}
    section[data-testid="stSidebar"] {display: none !important;}
    button[kind="header"] {display: none !important;}
    .css-1544g2n {display: none !important;}
    [data-testid="collapsedControl"] {display: none !important;}

    /* The PWA helper (inject_pwa_support) is a script-only 1x1 iframe. Keep
       it running but invisible: it drew a faint dash under the navbar. */
    [data-testid="stElementContainer"][height="1px"] > iframe[data-testid="stIFrame"] {
        opacity: 0 !important;
        pointer-events: none;
    }

    /* ===== Global Typography ===== */
    html, body, [class*="css"] {
        font-family: var(--font-family) !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    h1, h2, h3 {
        font-family: var(--font-display) !important;
        font-weight: 700;
        color: var(--color-primary);
        letter-spacing: -0.025em;
    }

    h4, h5, h6 {
        font-family: var(--font-family) !important;
        font-weight: 600;
        color: var(--color-primary);
    }

    h1 { font-weight: 700; letter-spacing: -0.035em; }

    /* ===== Utility Classes for Headers ===== */
    .page-title {
        font-family: var(--font-display) !important;
        font-size: 2.4rem !important;
        font-weight: 700 !important;
        line-height: 1.1 !important;
        letter-spacing: -0.035em;
        color: var(--color-primary) !important;
        margin: 0.5rem 0 0.5rem 0 !important;
        padding: 0 !important;
    }

    /* Small mono label above a title, as on the landing page */
    .bl-eyebrow {
        font-family: var(--font-mono) !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        line-height: 1.4 !important;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--color-accent) !important;
        margin: 0 !important;
    }

    /* Figures (prices, returns, ratios): DM Mono with aligned digits.
       DM Mono has no bold face, so the weight is pinned to avoid faux bold. */
    .bl-mono {
        font-family: var(--font-mono) !important;
        font-weight: 500 !important;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.01em;
    }

    .page-subtitle {
        color: var(--color-text-secondary);
        font-size: 1.05rem;
        line-height: 1.6;
        margin: 0;
    }

    /* ===== Step Headers ===== */
    .step-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1.25rem;
    }

    .step-circle {
        width: 32px;
        height: 32px;
        border-radius: var(--radius-sm);
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--color-accent-light);
        border: 1px solid rgba(46, 111, 199, 0.22);
        color: var(--color-accent) !important;
        font-family: var(--font-mono) !important;
        font-size: 0.9rem;
        font-weight: 500;
    }

    .step-title {
        font-weight: 700;
        font-size: 1.15rem;
        color: var(--color-primary);
        font-family: var(--font-display);
        letter-spacing: -0.01em;
    }

    p, li, div, label {
        color: var(--color-text);
        font-family: var(--font-family) !important;
    }

    /* ===== Page Background ===== */
    .stApp {
        background-color: var(--color-bg) !important;
    }

    /* ===== Layout ===== */
    .block-container,
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stMainBlockContainer"],
    .stMainBlockContainer {
        padding-top: 0 !important;
        padding-bottom: 2rem !important;
        padding-left: 3rem !important; /* Word document style margins */
        padding-right: 3rem !important;
        max-width: none !important; /* Completely destroy Streamlit max width limits */
    }

    /* Kill residual spacing on Streamlit wrappers */
    .main .block-container {
        padding-top: 0.5rem !important;
    }
    [data-testid="stAppViewContainer"] > .main {
        padding-top: 0 !important;
    }

    /* ===== Top Navigation Bar ===== */
    .bl-navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0;
        margin-top: -3.125rem; /* Ajustado para dejar exactamente 30px (~1.875rem) de margen superior */
        margin-bottom: 1rem;
        border-bottom: 1px solid var(--color-border-light);
    }

    .bl-navbar-brand {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        text-decoration: none;
        color: var(--color-primary);
    }

    .bl-navbar-brand img {
        height: 38px !important;
        max-height: 38px !important;
        width: auto !important;
        object-fit: contain !important;
    }

    .bl-navbar-links {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .bl-navbar-links a {
        text-decoration: none;
        color: var(--color-text-secondary);
        font-size: 0.9rem;
        font-weight: 500;
        padding: 0.5rem 1rem;
        border-radius: var(--radius-full);
        transition: var(--transition-fast);
    }

    .bl-navbar-links a:hover {
        color: var(--color-accent);
        background: var(--color-accent-light);
    }

    .bl-navbar-links a.active {
        color: var(--color-accent);
        background: var(--color-accent-light);
        font-weight: 600;
    }

    /* ===== Hero band (Home, About): navy, full width, as on the landing page ===== */
    .bl-band {
        /* Break out of the container's 3rem side padding to span the main
           area. Not 100vw: that includes the scrollbar, which shifts the band
           a few pixels off the content's left edge. */
        margin: -1rem -3rem 2.75rem -3rem;
        background:
            radial-gradient(900px 420px at 88% -10%, rgba(46, 111, 199, 0.30), transparent 65%),
            var(--color-primary);
        border-bottom: 1px solid var(--on-dark-line);
    }

    .bl-band-inner {
        padding: 3rem 3rem 2.6rem 3rem;
    }

    .bl-band .bl-eyebrow {
        color: var(--color-sky) !important;
    }

    .bl-band h1 {
        font-family: var(--font-display) !important;
        font-size: clamp(2.2rem, 4vw, 3.4rem) !important;
        font-weight: 700 !important;
        line-height: 1.06 !important;
        letter-spacing: -0.035em;
        color: #FFFFFF !important;
        margin: 0.9rem 0 1.1rem 0 !important;
        padding: 0 !important;
    }

    .bl-band h1 .accent {
        display: block;
        color: var(--color-sky) !important;
    }

    .bl-band p.bl-lead {
        color: var(--on-dark-2) !important;
        font-size: 1.1rem !important;
        line-height: 1.6 !important;
        max-width: 42rem;
        margin: 0 !important;
    }

    .bl-band-stats {
        display: grid;
        grid-template-columns: repeat(4, max-content);
        column-gap: 3rem;
        row-gap: 1.25rem;
        max-width: 42rem;
        margin: 2rem 0 0 0 !important;
        padding: 1.4rem 0 0 0 !important;
        border-top: 1px solid var(--on-dark-line);
    }

    .bl-band-stats dt {
        font-family: var(--font-mono) !important;
        font-size: 1.75rem;
        font-weight: 500;
        line-height: 1.1;
        color: #FFFFFF !important;
        font-variant-numeric: tabular-nums;
    }

    .bl-band-stats dd {
        margin: 0.3rem 0 0 0;
        font-size: 0.82rem;
        line-height: 1.35;
        color: var(--on-dark-2) !important;
    }

    /* Streamlit appends a hover "link to heading" icon to every markdown
       heading. Designed blocks are not document sections, so hide it there
       (in the band it would also drop onto an empty third title line). */
    .bl-band [data-testid="stHeaderActionElements"],
    .bl-block-head [data-testid="stHeaderActionElements"],
    .bl-steps [data-testid="stHeaderActionElements"],
    .bl-facts [data-testid="stHeaderActionElements"],
    .bl-tool-card [data-testid="stHeaderActionElements"] {
        display: none !important;
    }

    /* ===== Tool cards (Home) — equal height via Streamlit columns ===== */
    [data-testid="stHorizontalBlock"] {
        align-items: stretch;
    }

    .bl-tool-card {
        display: flex;
        flex-direction: column;
        height: 100%;
        background: var(--color-surface);
        border: 1px solid var(--color-line);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-card);
        overflow: hidden;
        text-decoration: none !important;
        color: inherit !important;
        transition: transform var(--transition-base), box-shadow var(--transition-base);
    }

    .bl-tool-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-lg);
    }

    .bl-tool-visual {
        min-height: 12rem;
        background: var(--color-surface-2);
        border-bottom: 1px solid var(--color-line);
        padding: 1rem 1.15rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        gap: 0.75rem;
    }

    .bl-tool-visual-head {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 0.4rem 0.75rem;
        font-family: var(--font-mono) !important;
        font-size: 0.75rem !important;
        color: var(--color-text-secondary) !important;
    }

    .bl-chips {
        display: flex;
        gap: 0.2rem;
    }

    .bl-chips span {
        font-size: 0.7rem;
        padding: 0.1rem 0.45rem;
        border-radius: var(--radius-full);
    }

    .bl-chips span.on {
        background: var(--color-accent);
        color: #FFFFFF !important;
    }

    /* Decorative candlesticks (example data): a wick <i> and a body <b> per
       candle, placed with inline top/height percentages */
    .bl-candles {
        display: flex;
        gap: 4px;
        height: 118px;
    }

    .bl-candles span {
        position: relative;
        flex: 1 1 0;
        color: var(--color-success);
    }

    .bl-candles span.dn {
        color: var(--color-error);
    }

    .bl-candles i,
    .bl-candles b {
        position: absolute;
        display: block;
        background: currentColor;
    }

    .bl-candles i {
        left: 50%;
        width: 1px;
        margin-left: -0.5px;
    }

    .bl-candles b {
        left: 0;
        right: 0;
        min-height: 2px;
        border-radius: 1px;
    }

    /* Example allocation bars */
    .bl-weights {
        display: grid;
        gap: 0.5rem;
    }

    .bl-w-row {
        display: grid;
        grid-template-columns: 1.4rem minmax(0, 1fr) 3rem;
        align-items: center;
        gap: 0.6rem;
        font-family: var(--font-mono) !important;
        font-size: 0.75rem !important;
        color: var(--color-text-secondary) !important;
        font-variant-numeric: tabular-nums;
    }

    .bl-w-row .pct {
        text-align: right;
        color: var(--color-primary) !important;
    }

    .bl-w-track {
        height: 12px;
        border-radius: var(--radius-full);
        background: var(--color-line);
        overflow: hidden;
    }

    .bl-w-fill {
        height: 100%;
        border-radius: var(--radius-full);
    }

    .bl-tool-body {
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
        flex: 1;
    }

    .bl-tool-body h3 {
        font-size: 1.45rem !important;
        line-height: 1.2 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    .bl-tool-body p {
        margin: 0 !important;
        color: var(--color-text-secondary) !important;
        line-height: 1.6;
    }

    .bl-checks {
        list-style: none;
        padding: 0 !important;
        margin: 0 !important;
        display: grid;
        gap: 0.55rem;
    }

    .bl-checks li {
        position: relative;
        padding-left: 1.75rem;
        margin: 0 !important;
        font-size: 0.94rem;
        line-height: 1.5;
        color: var(--color-text) !important;
    }

    /* Check mark in a soft blue circle, as on the landing page */
    .bl-checks li::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0.2rem;
        width: 1.1rem;
        height: 1.1rem;
        border-radius: 50%;
        background: var(--color-accent-light) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M3 6.2 5 8.2 9 4' fill='none' stroke='%232E6FC7' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / 12px no-repeat;
    }

    .bl-tool-link {
        margin-top: auto;
        padding-top: 0.35rem;
        font-weight: 600;
        color: var(--color-accent) !important;
    }

    .bl-tool-card:hover .bl-tool-link {
        text-decoration: underline;
        text-underline-offset: 3px;
    }

    /* ===== About: section heads, method steps, verification facts ===== */
    .bl-block-head {
        max-width: 46rem;
        margin: 0.5rem 0 1.75rem 0;
    }

    .bl-block-head h2 {
        font-size: clamp(1.6rem, 2.4vw, 2.1rem) !important;
        line-height: 1.15 !important;
        margin: 0.65rem 0 0.6rem 0 !important;
        padding: 0 !important;
    }

    .bl-block-head p.bl-block-lead {
        margin: 0 !important;
        font-size: 1.05rem;
        color: var(--color-text-secondary) !important;
    }

    .bl-steps {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1.75rem;
        margin: 0 0 3.5rem 0;
    }

    .bl-step {
        border-top: 2px solid var(--color-line-strong);
        padding-top: 1.1rem;
    }

    .bl-step-num {
        font-family: var(--font-mono) !important;
        font-size: 0.8rem;
        letter-spacing: 0.06em;
        color: var(--color-accent) !important;
    }

    .bl-step h3,
    .bl-fact h3 {
        font-size: 1.15rem !important;
        line-height: 1.3 !important;
        letter-spacing: -0.02em;
        margin: 0.55rem 0 0.4rem 0 !important;
        padding: 0 !important;
    }

    .bl-step p,
    .bl-fact p {
        margin: 0 !important;
        font-size: 0.94rem;
        line-height: 1.6;
        color: var(--color-text-secondary) !important;
    }

    .bl-facts {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        column-gap: 2.5rem;
        margin: 0 0 3.5rem 0;
    }

    .bl-fact {
        border-top: 1px solid var(--color-line);
        padding: 1rem 0 1.1rem 0;
    }

    .bl-fact h3 {
        margin-top: 0 !important;
    }

    /* ===== Buttons ===== */
    .stButton > button {
        border-radius: var(--radius-full) !important;
        font-family: var(--font-family) !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.7rem 2rem !important;
        transition: var(--transition-base) !important;
        letter-spacing: 0.01em !important;
        border: none !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-lg) !important;
    }

    .stButton > button[kind="primary"] {
        background: var(--color-accent) !important;
        color: white !important;
        border: none !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: var(--color-accent-hover) !important;
        box-shadow: var(--shadow-glow) !important;
    }

    .stButton > button[kind="secondary"],
    .stButton > button:not([kind="primary"]) {
        background: var(--color-surface) !important;
        color: var(--color-text) !important;
        border: 1.5px solid var(--color-border) !important;
    }

    .stButton > button[kind="secondary"]:hover,
    .stButton > button:not([kind="primary"]):hover {
        border-color: var(--color-accent) !important;
        color: var(--color-accent) !important;
        background: var(--color-accent-light) !important;
    }

    /* ===== Download button ===== */
    .stDownloadButton > button {
        border-radius: var(--radius-full) !important;
        font-family: var(--font-family) !important;
        font-weight: 600 !important;
        background: var(--color-accent) !important;
        color: white !important;
        border: none !important;
        padding: 0.7rem 2rem !important;
    }

    .stDownloadButton > button:hover {
        background: var(--color-accent-hover) !important;
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-glow) !important;
    }

    /* ===== Form Inputs ===== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        border-radius: var(--radius-md) !important;
        font-family: var(--font-family) !important;
        border: 1.5px solid var(--color-border) !important;
        padding: 0.7rem 1rem !important;
        transition: var(--transition-fast) !important;
        background: var(--color-surface) !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--color-accent) !important;
        box-shadow: 0 0 0 3px rgba(46, 111, 199, 0.1) !important;
    }

    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        border-radius: var(--radius-md) !important;
        font-family: var(--font-family) !important;
        border: 1.5px solid var(--color-border) !important;
    }

    .stSelectbox [data-baseweb="select"] {
        padding-top: 0.35rem !important;
        padding-bottom: 0.35rem !important;
    }

    .stSelectbox > div > div:focus,
    .stMultiSelect > div > div:focus-within {
        border-color: var(--color-accent) !important;
        box-shadow: 0 0 0 3px rgba(46, 111, 199, 0.1) !important;
    }

    /* ===== Checkboxes ===== */
    .stCheckbox label {
        font-weight: 500 !important;
        color: var(--color-text) !important;
    }

    /* ===== Tabs ===== */
    /* Streamlit 1.59 renders tabs with react-aria: a [role="tablist"] of
       div[role="tab"] (aria-selected), each label in a <p>. The BaseWeb
       selectors used before (data-baseweb="tab") no longer match anything,
       which left the active tab as dark text on a bare blue block. */
    .stTabs [role="tablist"] {
        gap: 0.25rem;
        width: fit-content;
        max-width: 100%;
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        padding: 4px;
        box-shadow: var(--shadow-xs);
    }

    /* Streamlit's full-width underline and sliding indicator */
    .stTabs [role="tablist"]::after,
    .stTabs .react-aria-SelectionIndicator {
        display: none !important;
    }

    .stTabs [role="tab"] {
        height: auto !important;
        padding: 0.45rem 1rem !important;
        border-radius: var(--radius-md);
        color: var(--color-text-secondary);
        transition: var(--transition-fast);
    }

    .stTabs [role="tab"] p {
        font-size: 0.875rem !important;
        font-weight: 500;
        color: inherit !important;
        margin: 0 !important;
        white-space: nowrap;
    }

    .stTabs [role="tab"]:hover {
        color: var(--color-accent);
        background: var(--color-accent-light);
    }

    .stTabs [role="tab"][aria-selected="true"] {
        background: var(--color-accent) !important;
        color: #FFFFFF !important;
        box-shadow: var(--shadow-sm);
    }

    .stTabs [role="tab"][aria-selected="true"] p {
        font-weight: 600;
    }

    /* ===== Info Boxes ===== */
    .bl-info {
        background: rgba(46, 111, 199, 0.08);
        border-left: 4px solid var(--color-accent);
        border-right: 1px solid var(--color-border);
        border-top: 1px solid var(--color-border);
        border-bottom: 1px solid var(--color-border);
        padding: 1.1rem 1.5rem;
        border-radius: 0 var(--radius-md) var(--radius-md) 0;
        margin: 1rem 0;
        font-size: 0.92rem;
        color: var(--color-text);
        line-height: 1.6;
    }

    .bl-success {
        background: rgba(16, 185, 129, 0.08);
        border-left: 4px solid var(--color-success);
        border-right: 1px solid var(--color-border);
        border-top: 1px solid var(--color-border);
        border-bottom: 1px solid var(--color-border);
        padding: 1.1rem 1.5rem;
        border-radius: 0 var(--radius-md) var(--radius-md) 0;
        margin: 1rem 0;
    }

    /* ===== Metrics ===== */
    [data-testid="stMetric"] {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        box-shadow: var(--shadow-sm);
        transition: var(--transition-base);
    }

    [data-testid="stMetric"]:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }

    [data-testid="stMetric"] label {
        font-family: var(--font-family) !important;
        font-size: 0.8rem !important;
        color: var(--color-text-secondary) !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Button labels are a <p> nested in divs inside the button, which the
       global `p, div` color rule reached first (dark slate on the blue
       primary buttons). Let every level inherit the button's own color. */
    .stButton > button div,
    .stButton > button p,
    .stDownloadButton > button div,
    .stDownloadButton > button p {
        color: inherit !important;
    }

    /* Target specific components */
    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] * {
        font-family: var(--font-mono) !important;
        font-weight: 500 !important;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.01em;
        color: var(--color-primary) !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
    }

    /* ===== Dividers ===== */
    hr {
        border: none;
        border-top: 1px solid var(--color-border-light);
        margin: 2rem 0;
    }

    /* ===== Expanders ===== */
    .streamlit-expanderHeader {
        font-family: var(--font-family) !important;
        font-weight: 600 !important;
        color: var(--color-text) !important;
        background: transparent !important;
        border-radius: var(--radius-md) !important;
    }

    details {
        border: 1px solid var(--color-border) !important;
        border-radius: var(--radius-md) !important;
        background: var(--color-surface) !important;
    }

    /* ===== Footer ===== */
    .bl-footer {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: flex-end;
        gap: 0.75rem 2rem;
        padding: 1.5rem 0 1.25rem 0;
        margin-top: 3.5rem;
        border-top: 1px solid var(--color-line);
    }

    .bl-footer,
    .bl-footer div {
        font-size: 0.85rem;
        color: var(--color-text-secondary);
    }

    .bl-footer .bl-footer-note {
        margin-top: 0.25rem;
        font-size: 0.78rem;
        color: var(--color-text-muted);
    }

    .bl-footer-links {
        display: flex;
        gap: 1.25rem;
    }

    .bl-footer a {
        color: var(--color-accent) !important;
        text-decoration: none;
        font-weight: 500;
    }

    .bl-footer a:hover {
        text-decoration: underline;
    }

    /* ===== Streamlit alert overrides ===== */
    .stAlert {
        border-radius: var(--radius-md) !important;
    }

    /* ===== Dataframes ===== */
    .stDataFrame {
        border-radius: var(--radius-md) !important;
        overflow: hidden;
    }

    /* ===== Spinner ===== */
    .stSpinner > div {
        border-top-color: var(--color-accent) !important;
    }

    /* ===== Page-specific: formula-box ===== */
    .formula-box {
        background: rgba(248, 250, 252, 0.8);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: 1.25rem 1.5rem;
        margin: 1rem 0;
        font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace;
        font-size: 1.05rem;
        color: var(--color-accent);
        font-weight: 600;
    }

    /* ===== Custom scrollbar ===== */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: var(--color-border);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--color-text-muted);
    }

    /* ===== Animations ===== */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .bl-animate {
        animation: fadeInUp 0.5s ease-out;
    }

    .bl-animate-delay-1 { animation-delay: 0.1s; animation-fill-mode: both; }
    .bl-animate-delay-2 { animation-delay: 0.2s; animation-fill-mode: both; }
    .bl-animate-delay-3 { animation-delay: 0.3s; animation-fill-mode: both; }
    .bl-animate-delay-4 { animation-delay: 0.4s; animation-fill-mode: both; }

    /* ===== Back link ===== */
    .bl-back-link {
        margin-bottom: 1.5rem;
    }

    .bl-back-link a {
        color: var(--color-accent);
        text-decoration: none;
        font-size: 0.9rem;
        font-weight: 500;
        transition: var(--transition-fast);
    }

    .bl-back-link a:hover {
        color: var(--color-accent-hover);
        text-decoration: underline;
    }

    /* ===== Mobile Responsiveness (PWA) ===== */
    @media (max-width: 768px) {
        /* Reduce lateral padding so charts and content have room. The div-
           qualified selectors match the specificity of the 3rem rule in
           inject_critical_css(); without them that rule won on phones too. */
        .block-container,
        [data-testid="stAppViewBlockContainer"],
        [data-testid="stMainBlockContainer"],
        .stMainBlockContainer,
        div[data-testid="stAppViewBlockContainer"],
        div.block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        .bl-navbar {
            padding: 0.75rem 1rem;
        }
        .bl-navbar-links {
            gap: 0.25rem;
        }
        .bl-navbar-links a {
            font-size: 0.8rem;
            padding: 0.4rem 0.6rem;
        }
        .page-title {
            font-size: 2rem !important;
        }
        .bl-band {
            margin-left: -1rem;
            margin-right: -1rem;
        }
        .bl-band-inner {
            padding: 2.25rem 1rem 2rem 1rem;
        }
        /* Band title: keep long words whole */
        .bl-band h1 {
            word-break: keep-all;
            overflow-wrap: break-word;
        }
        .bl-band-stats {
            grid-template-columns: repeat(2, minmax(0, 1fr));
            column-gap: 1.5rem;
        }
        .bl-steps {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .bl-facts {
            grid-template-columns: minmax(0, 1fr);
        }
        .step-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
        }
        /* Smaller tab text to fit more tabs */
        .stTabs [role="tab"] {
            padding: 0.4rem 0.55rem !important;
        }
        .stTabs [role="tab"] p {
            font-size: 0.78rem !important;
        }
        /* Make columns stack gracefully in Streamlit */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 1rem;
        }
    }

    @media (max-width: 480px) {
        /* Prevent any residual horizontal overflow */
        body, .stApp {
            overflow-x: hidden !important;
        }
        .bl-navbar {
            flex-direction: column;
            gap: 0.5rem;
        }
        .bl-navbar-links a {
            font-size: 0.72rem;
            padding: 0.35rem 0.5rem;
        }
        .page-title {
            font-size: 1.75rem !important;
        }
        .bl-steps {
            grid-template-columns: minmax(0, 1fr);
        }
        /* Even smaller tabs on very narrow screens */
        .stTabs [role="tab"] {
            padding: 0.35rem 0.45rem !important;
        }
        .stTabs [role="tab"] p {
            font-size: 0.72rem !important;
        }
    }
</style>
"""


# The navbar logo is served from Streamlit's static route (enableStaticServing)
# instead of being inlined as base64 on every rerun. It is a tight crop of
# assets/PortfolioLab.png, the same file the landing page uses
# (docs/assets/portfoliolab-logo.png). The path MUST stay relative: Streamlit
# Cloud mounts the app under /~/+/, and an absolute /app/static/... escapes
# that prefix (the edge answers with HTML and status 200, a blank image).
NAVBAR_LOGO_SRC = "./app/static/portfoliolab-logo.png"


def render_navbar(active_page: str = "home") -> None:
    """
    Render a modern top navigation bar with PortfolioLab logo.

    Args:
        active_page: Current page identifier ('home', 'stocks', 'portfolio', 'about')
    """
    home_class = 'class="active"' if active_page == "home" else ""
    stocks_class = 'class="active"' if active_page == "stocks" else ""
    portfolio_class = 'class="active"' if active_page == "portfolio" else ""
    about_class = 'class="active"' if active_page == "about" else ""

    st.markdown(f"""
    <div class="bl-navbar">
        <a href="/" target="_self" class="bl-navbar-brand">
            <img src="{NAVBAR_LOGO_SRC}" alt="PortfolioLab" width="100" height="38">
        </a>
        <div class="bl-navbar-links">
            <a href="/" target="_self" {home_class}>Home</a>
            <a href="/Stocks" target="_self" {stocks_class}>Stocks</a>
            <a href="/Portfolio" target="_self" {portfolio_class}>Portfolio</a>
            <a href="/About" target="_self" {about_class}>About</a>
        </div>
    </div>
    """, unsafe_allow_html=True)


def inject_critical_css() -> None:
    """
    Inject minimal CSS to hide sidebar and Streamlit chrome IMMEDIATELY.

    Call this right after st.set_page_config() — before any heavy imports —
    to prevent the sidebar flash that occurs when navigating between pages.
    The full design system CSS is injected later via inject_styles().
    """
    st.markdown("""
    <style>
        /* Hide sidebar and all Streamlit chrome instantly */
        [data-testid="stSidebar"],
        [data-testid="stSidebarNav"],
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        button[kind="header"],
        #MainMenu,
        header[data-testid="stHeader"],
        header,
        footer,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"] {
            display: none !important;
        }

        /* Hide the sidebar collapse button that can flash */
        .css-1544g2n,
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }

        /* ===== Aggressive Layout: Remove top gap & widen container ===== */
        header[data-testid="stHeader"], 
        .stApp > header {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
        }

        /* Use div with data-testid for ultra-high specificity to beat Emotion classes */
        div[data-testid="stAppViewBlockContainer"],
        div.block-container {
            padding-top: 0 !important;
            padding-left: 3rem !important; /* Word document style margins */
            padding-right: 3rem !important;
            max-width: none !important; /* Completely destroy Streamlit max width limits */
        }

        /* Prevent browser pinch-to-zoom on Plotly charts on mobile */
        .stPlotlyChart, .js-plotly-plot, .js-plotly-plot .plotly {
            touch-action: pan-y !important;
        }
    </style>
    """, unsafe_allow_html=True)


def inject_pwa_support() -> None:
    """Inject PWA manifest and service worker registration."""
    pwa_script = """
    <script>
    if (!parent.document.getElementById('pwa-manifest')) {
        // Resolve against the app's real base URL: on Streamlit Cloud the
        // app is mounted under /~/+/, so absolute /app/static/... paths
        // escape the prefix and return HTML instead of the asset.
        const staticBase = new URL('./app/static/', parent.document.baseURI).href;

        const manifest = parent.document.createElement('link');
        manifest.id = 'pwa-manifest';
        manifest.rel = 'manifest';
        manifest.href = staticBase + 'manifest.json';
        parent.document.head.appendChild(manifest);

        const theme = parent.document.createElement('meta');
        theme.name = 'theme-color';
        theme.content = '#0A1628';
        parent.document.head.appendChild(theme);

        const appleIcon = parent.document.createElement('link');
        appleIcon.rel = 'apple-touch-icon';
        appleIcon.href = staticBase + 'PortfolioLab.png';
        parent.document.head.appendChild(appleIcon);

        if ('serviceWorker' in parent.navigator) {
            parent.navigator.serviceWorker.register(staticBase + 'sw.js')
            .then(() => console.log('PortfolioLab PWA Service Worker registered'))
            .catch((err) => console.log('Service Worker registration failed:', err));
        }
    }
    </script>
    """
    # st.iframe requires positive dimensions (0 was valid in components.html);
    # 1x1 px keeps the script-only iframe effectively invisible.
    st.iframe(pwa_script, height=1, width=1)


def inject_styles() -> None:
    """Inject the shared CSS into the current Streamlit page."""
    st.markdown(get_shared_css(), unsafe_allow_html=True)
    inject_pwa_support()


def render_footer() -> None:
    """Renders the global footer at the bottom of the page."""
    st.markdown("""
    <div class="bl-footer">
        <div>
            <div>&copy; 2026 PortfolioLab &middot; Open source under the MIT License</div>
            <div class="bl-footer-note">For educational and informational purposes only — not investment advice. Market data provided by Yahoo Finance.</div>
        </div>
        <div class="bl-footer-links">
            <a href="https://jose062797.github.io/PortfolioLab/" target="_blank" rel="noopener">Website</a>
            <a href="https://github.com/Jose062797/PortfolioLab" target="_blank" rel="noopener">GitHub</a>
        </div>
    </div>
    """, unsafe_allow_html=True)
