"""
Shared Design System for PortfolioLab Platform

Modern design: clean, bold, no sidebar.
Top navigation bar, blue gradient accents matching logo, generous whitespace.
"""

import streamlit as st


def get_shared_css() -> str:
    """
    Return the complete shared CSS for the application.

    Includes:
    - Google Fonts (Inter + DM Sans)
    - Design tokens (blue palette matching PortfolioLab logo)
    - Streamlit chrome hiding + sidebar hiding
    - Top navigation bar
    - Modern typography, cards, buttons
    - Tool hub cards
    """
    return """
<style>
    /* ===== Google Fonts ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=DM+Sans:wght@400;500;700&display=swap');

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

        --gradient-primary: linear-gradient(135deg, #2E6FC7 0%, #1E5AB3 100%);
        --gradient-hero: linear-gradient(135deg, #0A1628 0%, #2E6FC7 100%);
        --gradient-card: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
        --gradient-accent: linear-gradient(135deg, #2E6FC7 0%, #3B82F6 100%);

        --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        --font-display: 'DM Sans', 'Inter', sans-serif;

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
        letter-spacing: -0.02em;
    }

    h4, h5, h6 {
        font-family: var(--font-family) !important;
        font-weight: 600;
        color: var(--color-primary);
    }

    h1 { font-weight: 800; letter-spacing: -0.03em; }

    /* ===== Utility Classes for Headers ===== */
    .page-title {
        font-family: var(--font-display) !important;
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        background: var(--gradient-hero);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.03em;
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
        color: white;
        font-size: 0.9rem;
        font-weight: 700;
        font-family: var(--font-display);
    }

    .step-circle.blue { background: var(--gradient-primary); }
    .step-circle.green { background: linear-gradient(135deg, #10B981, #34D399); }
    .step-circle.amber { background: linear-gradient(135deg, #F59E0B, #EF4444); }

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

    .bl-navbar-brand-icon {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        background: var(--gradient-accent);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 800;
        font-size: 0.85rem;
        font-family: var(--font-display);
    }

    .bl-navbar-brand-text {
        font-family: var(--font-display);
        font-weight: 700;
        font-size: 1.1rem;
        color: var(--color-primary);
    }

    .bl-navbar-brand img {
        height: 80px !important;
        max-height: 80px !important;
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

    /* ===== Hero Section with Image Background (Full Width Breakout) ===== */
    .bl-hero-bg {
        /* Break out of Streamlit's max-width container */
        width: 100vw !important;
        max-width: 100vw !important;
        position: relative;
        left: 50%;
        transform: translateX(-50%);
        margin-top: -1rem; /* Offset Streamlit top padding */
        margin-bottom: 3.5rem;
        
        overflow: hidden;
        background-size: cover;
        background-position: center;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 75vh;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }

    .bl-hero-overlay {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.85), rgba(30, 58, 138, 0.75));
        z-index: 1;
    }

    .bl-hero {
        text-align: center;
        padding: 4rem 2rem;
        max-width: 800px;
        position: relative;
        z-index: 2;
    }

    .bl-hero h1 {
        font-family: var(--font-display);
        font-size: 4rem;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 1.25rem;
        color: white;
        letter-spacing: -0.02em;
        text-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }

    .bl-hero p {
        font-size: 1.3rem;
        color: rgba(255, 255, 255, 0.9);
        line-height: 1.6;
        margin: 0 auto;
        text-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }

    /* ===== Cards ===== */
    .bl-card {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        padding: 1.75rem;
        box-shadow: var(--shadow-sm);
        transition: var(--transition-base);
        position: relative;
        overflow: hidden;
    }

    .bl-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--gradient-primary);
        opacity: 0;
        transition: var(--transition-base);
    }

    .bl-card:hover {
        box-shadow: var(--shadow-lg);
        transform: translateY(-4px);
        border-color: transparent;
    }

    .bl-card:hover::before {
        opacity: 1;
    }

    .bl-card-icon {
        width: 48px;
        height: 48px;
        border-radius: var(--radius-md);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
        margin-bottom: 1rem;
    }

    .bl-card-icon.blue { background: var(--color-accent-light); }
    .bl-card-icon.green { background: var(--color-success-light); }
    .bl-card-icon.amber { background: var(--color-warning-light); }

    .bl-card h4 {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: var(--color-primary);
    }

    .bl-card p {
        font-size: 0.92rem;
        color: var(--color-text-secondary);
        line-height: 1.65;
        margin: 0;
    }

    /* ===== Feature Card (large, with gradient) ===== */
    .bl-feature-card {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-xl);
        padding: 2.5rem;
        box-shadow: var(--shadow-md);
        position: relative;
        overflow: hidden;
    }

    .bl-feature-card::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle, rgba(46, 111, 199, 0.04) 0%, transparent 70%);
        pointer-events: none;
    }

    /* ===== Tool Hub Cards — equal height via Streamlit columns ===== */
    [data-testid="stHorizontalBlock"] {
        align-items: stretch;
    }
    /* ===== Modern Image Cards ===== */
    .bl-image-card {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-xl);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
        transition: var(--transition-base);
        display: flex;
        flex-direction: column;
        height: 100%;
        text-decoration: none !important;
        color: inherit !important;
    }

    .bl-image-card:hover {
        transform: translateY(-5px);
        box-shadow: var(--shadow-lg);
        border-color: var(--color-primary-light);
    }

    .bl-image-card-header {
        height: 180px;
        background-size: cover;
        background-position: center;
        border-bottom: 1px solid var(--color-border);
        transition: transform 0.5s ease;
    }

    .bl-image-card:hover .bl-image-card-header {
        transform: scale(1.03);
    }
    
    .bl-image-card-header-wrap {
        overflow: hidden;
        height: 180px;
    }

    .bl-image-card-body {
        padding: 2rem;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
        background: var(--color-surface);
        position: relative;
        z-index: 1;
    }

    .bl-image-card-body h3 {
        font-family: var(--font-display);
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--color-text);
        margin-bottom: 0.75rem;
    }

    .bl-image-card-body p {
        font-size: 1.05rem;
        color: var(--color-text-secondary);
        line-height: 1.6;
        margin-bottom: 1.5rem;
    }

    .bl-image-card-features {
        list-style: none;
        padding: 0;
        margin: 0 0 2rem 0;
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .bl-image-card-features li {
        font-size: 0.9rem;
        color: var(--color-text-tertiary);
        padding: 0.3rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .bl-image-card-btn {
        display: inline-block;
        align-self: center;
        width: auto;
        padding: 0.7rem 2rem;
        background: var(--gradient-accent);
        color: white !important;
        text-align: center;
        border-radius: var(--radius-full);
        font-family: var(--font-family);
        font-weight: 600;
        font-size: 0.95rem;
        text-decoration: none;
        transition: var(--transition-base);
        margin-top: auto;
        border: none;
        box-shadow: var(--shadow-sm);
        letter-spacing: 0.01em;
    }

    .bl-image-card-btn:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-glow);
        filter: brightness(1.1);
    }

    /* ===== Section Headers ===== */
    .bl-section-header {
        text-align: center;
        margin-bottom: 2.5rem;
    }

    .bl-section-header h2 {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }

    .bl-section-header p {
        color: var(--color-text-secondary);
        font-size: 1.05rem;
        max-width: 480px;
        margin: 0 auto;
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
        background: var(--gradient-accent) !important;
        color: white !important;
        border: none !important;
    }

    .stButton > button[kind="primary"]:hover {
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
        background: var(--gradient-accent) !important;
        color: white !important;
        border: none !important;
        padding: 0.7rem 2rem !important;
    }

    .stDownloadButton > button:hover {
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
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: var(--color-surface);
        border-radius: var(--radius-lg);
        padding: 4px;
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-xs);
    }

    .stTabs [data-baseweb="tab"] {
        font-family: var(--font-family) !important;
        font-weight: 500;
        font-size: 0.875rem;
        border-radius: var(--radius-md);
        padding: 0.5rem 1rem;
        color: var(--color-text-secondary);
        border: none !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--color-accent);
        background: var(--color-accent-light);
    }

    .stTabs [aria-selected="true"] {
        background: var(--color-accent) !important;
        color: white !important;
        font-weight: 600 !important;
        box-shadow: var(--shadow-sm) !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
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

    /* Add global custom styling for Primary Buttons */
    div[data-testid="stButton"] button[data-testid="baseButton-primary"] {
        background-color: #3b82f6 !important;
        color: white !important;
        border-radius: 24px !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2) !important;
    }
    div[data-testid="stButton"] button[data-testid="baseButton-primary"]:hover {
        background-color: #2563eb !important;
        box-shadow: 0 4px 6px rgba(59, 130, 246, 0.3) !important;
        transform: translateY(-1px) !important;
    }
    div[data-testid="stButton"] button[data-testid="baseButton-primary"]:active {
        transform: translateY(0px) !important;
    }

    /* Target specific components */
    [data-testid="stMetricValue"] {
        font-family: var(--font-display) !important;
        font-weight: 700 !important;
        color: var(--color-primary) !important;
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

    /* ===== Footer ===== */
    .bl-footer {
        text-align: center;
        padding: 2rem 0 1.5rem 0;
        margin-top: 3rem;
        border-top: 1px solid var(--color-border-light);
        color: var(--color-text-tertiary);
        font-size: 0.85rem;
        font-weight: 500;
        letter-spacing: 0.02em;
    }

    details {
        border: 1px solid var(--color-border) !important;
        border-radius: var(--radius-md) !important;
        background: var(--color-surface) !important;
    }

    /* ===== Footer ===== */
    .bl-footer {
        text-align: center;
        padding: 3rem 0 1.5rem 0;
        color: var(--color-text-muted);
        font-size: 0.85rem;
        border-top: 1px solid var(--color-border-light);
        margin-top: 3rem;
    }

    .bl-footer a {
        color: var(--color-accent);
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

    /* ===== Stats row ===== */
    .bl-stats {
        display: flex;
        justify-content: center;
        gap: 3rem;
        padding: 2rem 0;
        margin: 2rem 0;
        border-top: 1px solid var(--color-border-light);
        border-bottom: 1px solid var(--color-border-light);
    }

    .bl-stat {
        text-align: center;
    }

    .bl-stat-value {
        font-family: var(--font-display);
        font-size: 2rem;
        font-weight: 800;
        background: var(--gradient-accent);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .bl-stat-label {
        font-size: 0.85rem;
        color: var(--color-text-muted);
        font-weight: 500;
        margin-top: 0.25rem;
    }

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
        /* Reduce lateral padding so charts and content have room */
        .block-container,
        [data-testid="stAppViewBlockContainer"],
        [data-testid="stMainBlockContainer"],
        .stMainBlockContainer {
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
            font-size: 2rem;
        }
        /* Hero title: reduce size so long words don't break mid-character */
        .bl-hero h1 {
            font-size: 2.5rem;
            word-break: keep-all;
            overflow-wrap: break-word;
        }
        .step-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
        }
        /* Smaller tab text to fit more tabs */
        .stTabs [data-baseweb="tab"] {
            font-size: 0.78rem !important;
            padding: 0.4rem 0.55rem !important;
        }
        /* Make columns stack gracefully in Streamlit */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 1rem;
        }
        .bl-stats {
            flex-direction: column;
            gap: 1.5rem;
        }
        .bl-stat-value {
            font-size: 1.75rem;
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
            font-size: 1.75rem;
        }
        .bl-hero h1 {
            font-size: 2rem;
        }
        /* Even smaller tabs on very narrow screens */
        .stTabs [data-baseweb="tab"] {
            font-size: 0.72rem !important;
            padding: 0.35rem 0.45rem !important;
        }
    }
</style>
"""

import streamlit as st

@st.cache_data
def get_base64_of_bin_file(bin_file: str) -> str:
    """Read a binary file and return its base64 string."""
    import base64, os
    if not os.path.exists(bin_file):
        return ""
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

@st.cache_data
def _get_logo_base64(logo_path: str = "assets/PortfolioLab.png") -> str:
    """
    Read the logo image and return a base64-encoded data URI.

    The result is cached so the file is read only once per session.
    """
    base64_str = get_base64_of_bin_file(logo_path)
    if not base64_str:
        return ""
    return f"data:image/png;base64,{base64_str}"


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

    logo_src = _get_logo_base64()

    if logo_src:
        brand_html = f'<img src="{logo_src}" alt="PortfolioLab">'
    else:
        brand_html = (
            '<div class="bl-navbar-brand-icon">P</div>'
            '<span class="bl-navbar-brand-text">PortfolioLab</span>'
        )

    st.markdown(f"""
    <div class="bl-navbar">
        <a href="/" target="_self" class="bl-navbar-brand">
            {brand_html}
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
    import streamlit.components.v1 as components
    pwa_script = """
    <script>
    if (!parent.document.getElementById('pwa-manifest')) {
        const manifest = parent.document.createElement('link');
        manifest.id = 'pwa-manifest';
        manifest.rel = 'manifest';
        manifest.href = '/app/static/manifest.json';
        parent.document.head.appendChild(manifest);

        const theme = parent.document.createElement('meta');
        theme.name = 'theme-color';
        theme.content = '#0A1628';
        parent.document.head.appendChild(theme);
        
        const appleIcon = parent.document.createElement('link');
        appleIcon.rel = 'apple-touch-icon';
        appleIcon.href = '/app/static/PortfolioLab.png';
        parent.document.head.appendChild(appleIcon);

        if ('serviceWorker' in parent.navigator) {
            parent.navigator.serviceWorker.register('/app/static/sw.js')
            .then(() => console.log('PortfolioLab PWA Service Worker registered'))
            .catch((err) => console.log('Service Worker registration failed:', err));
        }
    }
    </script>
    """
    components.html(pwa_script, height=0, width=0)


def inject_styles() -> None:
    """Inject the shared CSS into the current Streamlit page."""
    st.markdown(get_shared_css(), unsafe_allow_html=True)
    inject_pwa_support()


def render_logo(logo_path: str = "assets/PortfolioLab.png") -> None:
    """Backward compatibility stub — logo is now part of navbar."""
    pass


def render_footer() -> None:
    """Renders the global footer at the bottom of the page."""
    st.markdown("""
    <div class="bl-footer">
        &copy; 2026 PortfolioLab. Professional Financial Analysis Platform.
    </div>
    """, unsafe_allow_html=True)

