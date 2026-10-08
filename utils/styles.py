"""
Shared Design System for PortfolioLab Platform

Light and plain (2026-09-27 redesign, guided by the ui-ux-pro-max skill:
"Minimalism & Swiss Style" for a financial tool): white cards on a pale
background, navy headings, one accent (the logo's blue), Inter for text and
figures (tabular digits), DM Sans for headings, sentence-case labels, no
emoji icons. The Home page (streamlit_app.py) is the public front door:
hero, example portfolios, the two tools, how it works.

MAINTENANCE MAP — Streamlit-internal selectors this module overrides
(these are the ONLY parts that can break when Streamlit updates; audit
them first after any `streamlit` version bump):

  - inject_critical_css():
      header[data-testid="stHeader"], [data-testid="stSidebar"],
      [data-testid="collapsedControl"], [data-testid="stToolbar"],
      section[data-testid="stSidebarNav"] — hide Streamlit chrome/sidebar.
      In 1.59 (checked 2026-10-08) only stHeader exists: with
      showSidebarNavigation = false the sidebar, its controls, the toolbar
      and the sidebar nav are not rendered at all. The other selectors are
      kept on purpose, as a guard if a Streamlit update brings them back.
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
      designed blocks); section[data-testid="stMain"] (a Tab stop in 1.59:
      the first one on every page, given a visible focus ring);
      [data-testid="stCaptionContainer"] (captions, darkened for contrast);
      .stPlotlyChart
      (touch-action); [data-testid="stExpander"] details; plus the same
      .block-container overrides for pages (the mobile one must match the
      specificity of inject_critical_css()).
  - Everything prefixed `bl-` (navbar, hero, example cards, tool cards,
      steps, footer) is OUR namespace and does not depend on Streamlit
      internals, except the tool cards, which are st.container(key=...)
      blocks (.st-key-bl-*) inside Streamlit's layout wrappers.

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
    - Google Fonts (Inter for text and figures, DM Sans for headings)
    - Design tokens (blue accent matching the PortfolioLab logo)
    - Streamlit chrome hiding + sidebar hiding
    - Top navigation bar
    - Typography, cards, buttons, tabs, metrics
    - Home: hero, example cards, tool cards, steps
    """
    return """
<style>
    /* ===== Google Fonts ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=DM+Sans:wght@500;700&display=swap');

    /* ===== Design Tokens ===== */
    :root {
        --color-primary: #0A1628;          /* navy: headings, strong figures */
        --color-accent: #2E6FC7;           /* the only accent (4.99:1 on white) */
        --color-accent-hover: #1E5AB3;
        --color-accent-light: rgba(46, 111, 199, 0.08);
        --color-success: #10B981;
        --color-warning: #F59E0B;
        --color-error: #EF4444;
        --color-bg: #F8FAFC;
        --color-surface: #FFFFFF;
        --color-surface-2: #F1F5F9;
        --color-border: #E2E8F0;
        --color-border-strong: #CBD5E1;
        --color-text: #334155;
        --color-text-secondary: #64748B;   /* 4.76:1 on white */
        --color-line: rgba(10, 22, 40, 0.10);

        --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        --font-display: 'DM Sans', 'Inter', sans-serif;

        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --radius-full: 9999px;

        --shadow-xs: 0 1px 2px rgba(15, 23, 42, 0.05);
        --shadow-card: 0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 16px rgba(15, 23, 42, 0.04);
        --shadow-card-hover: 0 1px 2px rgba(15, 23, 42, 0.06), 0 10px 28px rgba(15, 23, 42, 0.08);

        --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
        --transition-base: 200ms cubic-bezier(0.4, 0, 0.2, 1);
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

    /* ===== Global Typography ===== */
    html, body, [class*="css"] {
        font-family: var(--font-family) !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    /* Streamlit's markdown headings inherit their color from the enclosing
       div (the global rule below), so the navy needs !important */
    h1, h2, h3 {
        font-family: var(--font-display) !important;
        font-weight: 700;
        color: var(--color-primary) !important;
        letter-spacing: -0.02em;
        text-wrap: balance;
    }

    h4, h5, h6 {
        font-family: var(--font-family) !important;
        font-weight: 600;
        color: var(--color-primary) !important;
    }

    p, li, div, label {
        color: var(--color-text);
        font-family: var(--font-family) !important;
    }

    /* Figures (prices, returns, ratios): Inter with same-width digits, so
       columns of numbers line up and do not jump when they change */
    .bl-num {
        font-variant-numeric: tabular-nums;
        font-feature-settings: "tnum" 1;
    }

    .js-plotly-plot .plotly text {
        font-variant-numeric: tabular-nums;
    }

    /* ===== Page headers (Stocks, Portfolio, About) ===== */
    .page-title {
        font-family: var(--font-display) !important;
        font-size: 2.25rem !important;
        font-weight: 700 !important;
        line-height: 1.15 !important;
        letter-spacing: -0.03em;
        color: var(--color-primary) !important;
        margin: 0.5rem 0 0.4rem 0 !important;
        padding: 0 !important;
    }

    .page-subtitle {
        color: var(--color-text-secondary) !important;
        font-size: 1.05rem;
        line-height: 1.6;
        max-width: 44rem;
        margin: 0 !important;
    }

    /* ===== Step headers (Portfolio form: 1, 2, 3) ===== */
    .step-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 1rem;
    }

    .step-circle {
        width: 28px;
        height: 28px;
        flex: none;
        border-radius: var(--radius-full);
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--color-accent-light);
        color: var(--color-accent) !important;
        font-size: 0.85rem;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
    }

    .step-title {
        font-weight: 700;
        font-size: 1.15rem;
        color: var(--color-primary);
        font-family: var(--font-display) !important;
        letter-spacing: -0.01em;
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

    /* ===== Focus: visible for keyboard users on everything clickable ===== */
    /* Solid accent (4.99:1 on white). Until 2026-10-08 it was the 35% ring
       token, about 2:1, below the 3:1 a focus indicator needs (audit F3-02). */
    a:focus-visible,
    button:focus-visible,
    [role="tab"]:focus-visible,
    [role="tabpanel"]:focus-visible,
    summary:focus-visible {
        outline: 3px solid var(--color-accent) !important;
        outline-offset: 2px;
    }

    /* Streamlit makes its main scroll area a Tab stop (tabindex=0) so the
       keyboard can scroll it; it is the first stop on every page, so it gets
       the same ring, drawn inside the edge. */
    section[data-testid="stMain"]:focus-visible {
        outline: 3px solid var(--color-accent) !important;
        outline-offset: -3px;
    }

    /* st.caption: Streamlit draws it at opacity 0.6, which measured 3.3:1 on
       the page background (axe, 2026-10-08). Full opacity and the secondary
       text token give 4.56:1 there and 4.76:1 on white. */
    [data-testid="stCaptionContainer"] {
        opacity: 1 !important;
    }
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p {
        color: var(--color-text-secondary) !important;
    }

    /* Section headings drawn as divs with role="heading" (subheading_html):
       the look of the old #### headings, with a correct outline level. */
    .bl-subhead {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        line-height: 1.2 !important;
        color: var(--color-primary) !important;
        padding: 0.5rem 0 1rem 0;
        margin: 0;
    }

    /* ===== Top Navigation Bar ===== */
    .bl-navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0;
        margin-top: -3.125rem; /* leaves exactly 30px (~1.875rem) above the navbar */
        margin-bottom: 1rem;
        border-bottom: 1px solid var(--color-border);
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
        font-size: 0.92rem;
        font-weight: 500;
        padding: 0.5rem 0.95rem;
        border-radius: var(--radius-full);
        transition: color var(--transition-fast), background var(--transition-fast);
    }

    .bl-navbar-links a:hover {
        color: var(--color-primary);
        background: var(--color-surface-2);
    }

    .bl-navbar-links a.active {
        /* The darker accent: the plain one measured 4.3:1 on this tint,
           below the 4.5:1 text needs (axe, 2026-10-08) */
        color: var(--color-accent-hover);
        background: var(--color-accent-light);
        font-weight: 600;
    }

    /* Streamlit appends a hover "link to heading" icon to every markdown
       heading. Page titles and designed blocks are not document sections, so
       hide it there. */
    .page-title [data-testid="stHeaderActionElements"],
    .bl-hero [data-testid="stHeaderActionElements"],
    .bl-section-head [data-testid="stHeaderActionElements"],
    .bl-steps [data-testid="stHeaderActionElements"],
    .bl-tool-body [data-testid="stHeaderActionElements"] {
        display: none !important;
    }

    /* ===== Home: hero ===== */
    /* A pale blue wash under the navbar. The negative side margins cancel the
       page's 3rem padding (1rem on phones) so the wash spans the page. */
    .bl-hero {
        margin: -1rem -3rem 0 -3rem;
        padding: 4.5rem 3rem 3.25rem 3rem;
        text-align: center;
        background: linear-gradient(180deg, #E8F0FB 0%, rgba(248, 250, 252, 0) 100%);
    }

    .bl-hero h1 {
        font-size: clamp(2.3rem, 5vw, 3.6rem) !important;
        line-height: 1.08 !important;
        letter-spacing: -0.035em;
        max-width: 18ch;
        margin: 0 auto 1.1rem auto !important;
        padding: 0 !important;
    }

    .bl-hero p.bl-lead {
        font-size: 1.15rem !important;
        line-height: 1.65 !important;
        color: var(--color-text-secondary) !important;
        max-width: 40rem;
        margin: 0 auto !important;
    }

    .bl-ctas {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 0.75rem;
        margin: 2rem 0 0 0;
    }

    /* Links styled as buttons (relative hrefs, see render_navbar) */
    .bl-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.45rem;
        min-height: 44px;
        padding: 0.7rem 1.4rem;
        border-radius: var(--radius-full);
        font-weight: 600;
        font-size: 1rem;
        line-height: 1.2;
        text-decoration: none !important;
        cursor: pointer;
        transition: background var(--transition-fast), border-color var(--transition-fast),
                    color var(--transition-fast);
    }

    .bl-btn-primary {
        background: var(--color-accent);
        color: #FFFFFF !important;
    }

    .bl-btn-primary:hover {
        background: var(--color-accent-hover);
    }

    .bl-btn-secondary {
        background: var(--color-surface);
        border: 1px solid var(--color-border-strong);
        color: var(--color-primary) !important;
    }

    .bl-btn-secondary:hover {
        border-color: var(--color-accent);
        color: var(--color-accent) !important;
    }

    .bl-hero p.bl-hero-meta {
        margin: 1.4rem 0 0 0 !important;
        font-size: 0.9rem !important;
        color: var(--color-text-secondary) !important;
    }

    /* ===== Home: sections ===== */
    .bl-section-head {
        text-align: center;
        max-width: 42rem;
        margin: 3.5rem auto 1.75rem auto;
    }

    .bl-section-head h2 {
        font-size: clamp(1.6rem, 2.6vw, 2.1rem) !important;
        line-height: 1.2 !important;
        margin: 0 0 0.5rem 0 !important;
        padding: 0 !important;
    }

    .bl-section-head p {
        margin: 0 !important;
        font-size: 1.05rem;
        line-height: 1.6;
        color: var(--color-text-secondary) !important;
    }

    /* Example portfolios: each card is one link to the filled-in form */
    .bl-examples {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1.25rem;
    }

    a.bl-example {
        display: flex;
        flex-direction: column;
        gap: 0.8rem;
        padding: 1.35rem 1.4rem 1.25rem 1.4rem;
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-card);
        text-decoration: none !important;
        cursor: pointer;
        transition: border-color var(--transition-base), box-shadow var(--transition-base);
    }

    a.bl-example:hover {
        border-color: rgba(46, 111, 199, 0.45);
        box-shadow: var(--shadow-card-hover);
    }

    .bl-example-title {
        font-family: var(--font-display) !important;
        font-size: 1.2rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: var(--color-primary) !important;
    }

    .bl-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
    }

    .bl-chip {
        padding: 0.2rem 0.6rem;
        border-radius: var(--radius-full);
        background: var(--color-surface-2);
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--color-primary) !important;
    }

    .bl-example-goal {
        font-size: 0.95rem;
        line-height: 1.5;
        color: var(--color-text) !important;
    }

    .bl-example-open {
        margin-top: auto;
        padding-top: 0.25rem;
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--color-accent) !important;
    }

    a.bl-example:hover .bl-example-open {
        text-decoration: underline;
        text-underline-offset: 3px;
    }

    /* Tool cards: each card is an st.container, because it holds a Plotly
       chart: .st-key-bl-card-* is the card, .st-key-bl-visual-* its chart
       area and the text below is .bl-tool-body markdown. The columns stretch
       to the taller card, and each card fills its column. */
    [data-testid="stHorizontalBlock"] {
        align-items: stretch;
    }

    [data-testid="stColumn"]:has(.st-key-bl-card-stocks) > [data-testid="stVerticalBlock"],
    [data-testid="stColumn"]:has(.st-key-bl-card-portfolio) > [data-testid="stVerticalBlock"] {
        height: 100%;
    }

    /* Streamlit wraps each container in a layout wrapper that does not grow */
    [data-testid="stLayoutWrapper"]:has(> .st-key-bl-card-stocks),
    [data-testid="stLayoutWrapper"]:has(> .st-key-bl-card-portfolio) {
        flex: 1 1 auto;
    }

    .st-key-bl-card-stocks,
    .st-key-bl-card-portfolio {
        flex: 1 1 auto;
        gap: 0 !important;
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-card);
        overflow: hidden;
    }

    .st-key-bl-visual-stocks,
    .st-key-bl-visual-portfolio {
        padding: 1rem 1.15rem 0.75rem 1.15rem;
        border-bottom: 1px solid var(--color-border);
        gap: 0.4rem !important;
    }

    /* Head line of a chart card: what it shows, and an "Example" tag */
    .bl-fig-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.75rem;
        font-size: 0.85rem !important;
        color: var(--color-text-secondary) !important;
    }

    .bl-tag {
        padding: 0.1rem 0.6rem;
        border-radius: var(--radius-full);
        background: var(--color-surface-2);
        font-size: 0.78rem;
        font-weight: 500;
        white-space: nowrap;
    }

    /* Headline figures under the Portfolio card's chart */
    .bl-metrics {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 0.3rem 1.25rem;
        padding-top: 0.6rem;
        border-top: 1px solid var(--color-border);
        font-size: 0.85rem !important;
        color: var(--color-text-secondary) !important;
        font-variant-numeric: tabular-nums;
    }

    .bl-metrics b {
        color: var(--color-primary) !important;
        font-weight: 600;
    }

    .bl-tool-body {
        padding: 1.4rem 1.5rem 1.5rem 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.7rem;
    }

    .bl-tool-body h3 {
        font-size: 1.4rem !important;
        line-height: 1.2 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    .bl-tool-body p {
        margin: 0 !important;
        color: var(--color-text-secondary) !important;
        line-height: 1.6;
    }

    a.bl-tool-link {
        align-self: flex-start;
        padding-top: 0.25rem;
        font-weight: 600;
        color: var(--color-accent) !important;
        text-decoration: none !important;
    }

    a.bl-tool-link:hover {
        text-decoration: underline !important;
        text-underline-offset: 3px;
    }

    /* How it works: three numbered steps */
    .bl-steps {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1.25rem;
    }

    .bl-step {
        padding: 1.35rem 1.4rem;
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
    }

    .bl-step-num {
        width: 2rem;
        height: 2rem;
        display: grid;
        place-items: center;
        border-radius: var(--radius-full);
        background: var(--color-accent-light);
        color: var(--color-accent) !important;
        font-weight: 700;
        font-size: 0.95rem;
    }

    .bl-step h3 {
        font-size: 1.15rem !important;
        line-height: 1.3 !important;
        margin: 0.85rem 0 0.35rem 0 !important;
        padding: 0 !important;
    }

    .bl-step p {
        margin: 0 !important;
        font-size: 0.95rem;
        line-height: 1.6;
        color: var(--color-text-secondary) !important;
    }

    /* ===== Buttons ===== */
    .stButton > button {
        border-radius: var(--radius-full) !important;
        font-family: var(--font-family) !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        min-height: 44px;
        padding: 0.6rem 1.75rem !important;
        transition: background var(--transition-fast), border-color var(--transition-fast),
                    color var(--transition-fast) !important;
        border: none !important;
    }

    .stButton > button[kind="primary"] {
        background: var(--color-accent) !important;
        color: white !important;
        border: none !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: var(--color-accent-hover) !important;
    }

    .stButton > button[kind="primary"]:disabled {
        background: var(--color-border-strong) !important;
        color: #FFFFFF !important;
    }

    .stButton > button[kind="secondary"],
    .stButton > button:not([kind="primary"]) {
        background: var(--color-surface) !important;
        color: var(--color-primary) !important;
        border: 1px solid var(--color-border-strong) !important;
    }

    .stButton > button[kind="secondary"]:hover,
    .stButton > button:not([kind="primary"]):hover {
        border-color: var(--color-accent) !important;
        color: var(--color-accent) !important;
    }

    /* ===== Download button ===== */
    .stDownloadButton > button {
        border-radius: var(--radius-full) !important;
        font-family: var(--font-family) !important;
        font-weight: 600 !important;
        min-height: 44px;
        background: var(--color-accent) !important;
        color: white !important;
        border: none !important;
        padding: 0.6rem 1.75rem !important;
    }

    .stDownloadButton > button:hover {
        background: var(--color-accent-hover) !important;
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

    /* ===== Form Inputs ===== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        border-radius: var(--radius-md) !important;
        font-family: var(--font-family) !important;
        border: 1px solid var(--color-border-strong) !important;
        padding: 0.65rem 0.9rem !important;
        transition: border-color var(--transition-fast), box-shadow var(--transition-fast) !important;
        background: var(--color-surface) !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--color-accent) !important;
        box-shadow: 0 0 0 3px var(--color-accent-light) !important;
    }

    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        border-radius: var(--radius-md) !important;
        font-family: var(--font-family) !important;
        border: 1px solid var(--color-border-strong) !important;
    }

    .stSelectbox [data-baseweb="select"] {
        padding-top: 0.3rem !important;
        padding-bottom: 0.3rem !important;
    }

    .stSelectbox > div > div:focus,
    .stMultiSelect > div > div:focus-within {
        border-color: var(--color-accent) !important;
        box-shadow: 0 0 0 3px var(--color-accent-light) !important;
    }

    /* ===== Checkboxes ===== */
    .stCheckbox label {
        font-weight: 500 !important;
        color: var(--color-text) !important;
    }

    /* ===== Tabs: a segmented control ===== */
    /* Streamlit 1.59 renders tabs with react-aria: a [role="tablist"] of
       div[role="tab"] (aria-selected), each label in a <p>. The BaseWeb
       selectors used before (data-baseweb="tab") no longer match anything,
       which left the active tab as dark text on a bare blue block. */
    .stTabs [role="tablist"] {
        gap: 0.2rem;
        width: fit-content;
        max-width: 100%;
        background: var(--color-surface-2);
        border-radius: var(--radius-md);
        padding: 4px;
    }

    /* Streamlit's full-width underline and sliding indicator */
    .stTabs [role="tablist"]::after,
    .stTabs .react-aria-SelectionIndicator {
        display: none !important;
    }

    .stTabs [role="tab"] {
        height: auto !important;
        padding: 0.45rem 1rem !important;
        border-radius: var(--radius-sm);
        color: var(--color-text-secondary);
        transition: color var(--transition-fast), background var(--transition-fast);
    }

    .stTabs [role="tab"] p {
        font-size: 0.9rem !important;
        font-weight: 500;
        color: inherit !important;
        margin: 0 !important;
        white-space: nowrap;
    }

    .stTabs [role="tab"]:hover {
        color: var(--color-primary);
    }

    .stTabs [role="tab"][aria-selected="true"] {
        background: var(--color-surface) !important;
        color: var(--color-primary) !important;
        box-shadow: var(--shadow-xs), 0 0 0 1px var(--color-border);
    }

    .stTabs [role="tab"][aria-selected="true"] p {
        font-weight: 600;
    }

    /* ===== Metrics ===== */
    [data-testid="stMetric"] {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: 1rem 1.2rem;
    }

    [data-testid="stMetric"] label,
    [data-testid="stMetricLabel"] p {
        font-family: var(--font-family) !important;
        font-size: 0.88rem !important;
        color: var(--color-text-secondary) !important;
        font-weight: 500 !important;
    }

    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] * {
        font-family: var(--font-family) !important;
        font-weight: 600 !important;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.02em;
        color: var(--color-primary) !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.55rem !important;
    }

    /* Labels wrap instead of being cut ("Expected re…"): Streamlit sets
       nowrap + ellipsis on the label's <p> and its markdown container */
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricLabel"] [data-testid="stMarkdownContainer"] {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }

    /* Five cards in a row get narrow before the columns stack (about 640
       px): every label keeps room for two lines, so the figures stay level */
    @media (min-width: 641px) and (max-width: 1100px) {
        [data-testid="stMetricLabel"] {
            min-height: 2.6em;
            align-items: flex-start;
        }
    }

    /* ===== Dividers ===== */
    hr {
        border: none;
        border-top: 1px solid var(--color-border);
        margin: 2rem 0;
    }

    /* ===== Expanders ===== */
    [data-testid="stExpander"] details,
    details {
        border: 1px solid var(--color-border) !important;
        border-radius: var(--radius-md) !important;
        background: var(--color-surface) !important;
    }

    [data-testid="stExpander"] summary p {
        font-weight: 600 !important;
        color: var(--color-primary) !important;
    }

    /* ===== Stocks: period returns strip (pages/1_Stocks.py) ===== */
    .bl-returns {
        display: grid;
        grid-template-columns: repeat(8, minmax(0, 1fr));
        border: 1px solid var(--color-border);
        border-radius: 8px;
        background: white;
        margin: 0.5rem 0 1rem 0;
    }

    .bl-returns > div {
        text-align: center;
        padding: 7px 4px;
        min-width: 0;
    }

    .bl-returns .bl-returns-label {
        font-size: 0.78rem !important;
        color: var(--color-text-secondary) !important;
    }

    .bl-returns .bl-returns-value {
        font-size: 0.9rem !important;
        font-weight: 600;
        overflow-wrap: anywhere;
    }

    @media (max-width: 640px) {
        .bl-returns {
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }
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
        border-top: 1px solid var(--color-border);
    }

    .bl-footer,
    .bl-footer div {
        font-size: 0.85rem;
        color: var(--color-text-secondary);
    }

    .bl-footer .bl-footer-note {
        margin-top: 0.25rem;
    }

    .bl-footer-links {
        display: flex;
        gap: 1.25rem;
    }

    .bl-footer a {
        color: var(--color-accent) !important;
        text-decoration: none;
        font-weight: 500;
        /* A 44 px touch target, like the rest of the page (audit F4-02) */
        display: inline-flex;
        align-items: center;
        min-height: 44px;
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

    /* ===== Custom scrollbar ===== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: var(--color-border-strong);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--color-text-secondary);
    }

    /* ===== Reduced motion: no transitions for users who ask for none ===== */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            transition: none !important;
            animation: none !important;
            scroll-behavior: auto !important;
        }
    }

    /* ===== Tablets: the example cards and steps stack ===== */
    @media (max-width: 1000px) {
        .bl-examples,
        .bl-steps {
            grid-template-columns: minmax(0, 1fr);
            max-width: 36rem;
            margin-left: auto;
            margin-right: auto;
        }
    }

    /* ===== Mobile Responsiveness ===== */
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
            padding: 0.75rem 0;
        }
        .bl-navbar-links {
            gap: 0.15rem;
        }
        .bl-navbar-links a {
            font-size: 0.85rem;
            padding: 0.5rem 0.65rem;
        }
        .page-title {
            font-size: 1.9rem !important;
        }
        .bl-hero {
            margin-left: -1rem;
            margin-right: -1rem;
            padding: 3rem 1rem 2.25rem 1rem;
        }
        .bl-section-head {
            margin-top: 2.75rem;
        }
        .step-header {
            margin-bottom: 0.75rem;
        }
        /* Smaller tab text to fit more tabs */
        .stTabs [role="tab"] {
            padding: 0.4rem 0.6rem !important;
        }
        .stTabs [role="tab"] p {
            font-size: 0.82rem !important;
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
            font-size: 0.8rem;
            padding: 0.5rem 0.55rem;
        }
        .page-title {
            font-size: 1.75rem !important;
        }
        .bl-ctas .bl-btn {
            width: 100%;
        }
        /* Even smaller tabs on very narrow screens */
        .stTabs [role="tab"] {
            padding: 0.35rem 0.45rem !important;
        }
        .stTabs [role="tab"] p {
            font-size: 0.76rem !important;
        }
    }
</style>
"""


# The navbar logo is served from Streamlit's static route (enableStaticServing)
# instead of being inlined as base64 on every rerun. It is a tight crop of
# assets/PortfolioLab.png (which the PDF uses). The path MUST stay relative: Streamlit
# Cloud mounts the app under /~/+/, and an absolute /app/static/... escapes
# that prefix (the edge answers with HTML and status 200, a blank image).
NAVBAR_LOGO_SRC = "./app/static/portfoliolab-logo.png"


def render_navbar(active_page: str = "home") -> None:
    """
    Render a modern top navigation bar with PortfolioLab logo.

    Args:
        active_page: Current page identifier ('home', 'stocks', 'portfolio', 'about')
    """
    def _link(href: str, label: str, page: str) -> str:
        current = ' class="active" aria-current="page"' if active_page == page else ""
        return f'<a href="{href}" target="_self"{current}>{label}</a>'

    # Links MUST be relative, like the static URLs above. On Streamlit Cloud
    # the app runs in an iframe at /~/+/; an absolute "/Stocks" made that
    # iframe load the whole platform page inside itself (pages nested one
    # level deeper per click, address bar stuck on the first page). "./Stocks"
    # stays inside /~/+/, and the platform then updates the address bar.
    st.markdown(f"""
    <nav class="bl-navbar" aria-label="Main">
        <a href="./" target="_self" class="bl-navbar-brand">
            <img src="{NAVBAR_LOGO_SRC}" alt="PortfolioLab" width="100" height="38">
        </a>
        <div class="bl-navbar-links">
            {_link("./", "Home", "home")}
            {_link("./Stocks", "Stocks", "stocks")}
            {_link("./Portfolio", "Portfolio", "portfolio")}
            {_link("./About", "About", "about")}
        </div>
    </nav>
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


# No PWA since 2026-10-08 (audit B5-04, F3-01). inject_pwa_support() added a
# manifest and a service worker through a 1x1 st.iframe, but inside Streamlit
# Cloud's frame the worker's scope (./app/static/) never controlled the app,
# the manifest's start_url answered 404, and the invisible iframe was the
# first Tab stop on every page. Workers already registered in visitors'
# browsers only cover the static folder and go to the network first.


def inject_styles() -> None:
    """Inject the shared CSS into the current Streamlit page."""
    st.markdown(get_shared_css(), unsafe_allow_html=True)


def subheading_html(text: str, level: int) -> str:
    """
    A section heading that looks like the old `####` markdown ones while
    giving assistive technology the right outline level (h1 page title, h2
    form steps, h3 sections within them; audit F3-04). `text` must be a
    constant: it goes into raw HTML.
    """
    return f'<div class="bl-subhead" role="heading" aria-level="{level}">{text}</div>'


def render_footer() -> None:
    """Renders the global footer at the bottom of the page."""
    # A div with the footer role, not <footer>: the CSS hides every <footer>
    # to remove Streamlit's own.
    st.markdown("""
    <div class="bl-footer" role="contentinfo">
        <div>
            <div>&copy; 2026 PortfolioLab &middot; Open source under the MIT License</div>
            <div class="bl-footer-note">For educational and informational purposes only — not investment advice. Market data provided by Yahoo Finance.</div>
        </div>
        <div class="bl-footer-links">
            <a href="https://github.com/Jose062797/PortfolioLab" target="_blank" rel="noopener">Source on GitHub</a>
        </div>
    </div>
    """, unsafe_allow_html=True)
