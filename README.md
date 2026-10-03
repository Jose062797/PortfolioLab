# PortfolioLab

[![Tests](https://github.com/Jose062797/PortfolioLab/actions/workflows/tests.yml/badge.svg)](https://github.com/Jose062797/PortfolioLab/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.14-blue.svg)](https://www.python.org/)

**PortfolioLab** is an open-source financial platform built with Streamlit, for learning. It provides tools to explore assets, build portfolios and analyze their performance.

### 🚀 [Open the app](https://portfoliolab-qzrhvh2p5ls7xqhyx38smv.streamlit.app/)

> For educational and informational purposes only — not investment advice.

---

## Features

### 📊 Stocks
Interactive dashboard to explore any asset available on Yahoo Finance (stocks, ETFs, indices, crypto).
- Line and candlestick charts with volume, from one day to the full history (Yahoo Finance data, refreshed every few minutes)
- Key statistics: price, market cap, volume, 52-week range
- Period returns from 1D to All
- For stocks: YTD, 1Y, 3Y and 5Y price returns compared with the S&P 500 (^GSPC), and quarterly revenue vs. earnings

### 📈 Portfolio Optimizer
Portfolio construction engine supporting two mathematical models:
- **Markowitz (Mean-Variance)**: four goals in plain words — lowest risk (min variance), best return for the risk (max Sharpe), highest return within a risk limit, and lowest risk for a target return — with a choice of expected-returns estimator (CAPM or historical mean, for non-equity assets)
- **Black-Litterman**: Bayesian optimization combining market equilibrium with custom investor views
- Efficient frontier visualization, historical backtesting, and correlation analysis
- Overlapping-holdings detection (flags near-perfectly correlated assets, e.g. two funds that track the same index)
- Downloadable PDF reports with full breakdown
- Example portfolios on the Home page that open the tool with the form filled in

The mathematical engine is verified to produce output **identical to raw
[PyPortfolioOpt](https://pyportfolioopt.readthedocs.io/)** across all
optimization paths — enforced permanently by a parity test suite and frozen
numeric regression snapshots.

---

## Requirements

- **Python 3.12 or newer** (verified working on Python 3.14)
- On Windows without MSVC build tools, `ecos` may fail to install on Python ≥3.13 — it is safe to skip it locally; the app falls back to a greedy allocation method
- Internet connection (to fetch market data from Yahoo Finance)

---

## Installation

```powershell
# 1. Clone the repository
git clone https://github.com/Jose062797/PortfolioLab.git
cd PortfolioLab

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run streamlit_app.py
```

The app will open at `http://localhost:8501`.

---

## Project Structure

```
├── streamlit_app.py          # Home page & entry point
├── pages/
│   ├── 1_Stocks.py           # Stock/asset exploration tool
│   ├── 2_Portfolio.py        # Portfolio optimization tool
│   └── 3_About.py            # Documentation & methodology
├── core/                     # Framework-independent business logic
│   ├── opt_engine.py         # Math engine (Markowitz & Black-Litterman)
│   ├── backtest.py           # Historical simulation
│   ├── data_provider.py      # yfinance data layer
│   ├── pdf_shared.py         # Shared PDF chart builders
│   ├── constants.py          # Centralized constants
│   └── example_market.py     # Home page examples (portfolios and example charts)
├── utils/                    # Streamlit integration layer
│   ├── styles.py             # Design system & CSS
│   ├── visualizations.py     # Plotly interactive charts
│   ├── optimizer_wrapper.py  # UI ↔ core bridge
│   ├── pdf_generator.py      # Web PDF export
│   └── session_manager.py    # Streamlit session state
├── tests/                    # pytest test suite (parity, regression, edge cases)
├── static/                   # Navbar logo and PWA assets
├── assets/                   # Logo, favicon, Home example result
└── .github/workflows/        # CI (pytest on Python 3.12 & 3.14)
```

---

## Running Tests

```powershell
pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests\ -v
```

The suite (140 tests) runs fully offline against synthetic fixtures and covers:
mathematical parity with raw PyPortfolioOpt, frozen numeric regression
snapshots, numerical edge cases, data-layer failure modes, input validation,
PDF/visualization outputs, and backtest conventions. It also runs automatically
on every push to `main` and every pull request via GitHub Actions (Python 3.12
and 3.14).

---

## Privacy

When you **run PortfolioLab locally**, all calculations happen on your machine:
no portfolio data or investment views are sent to external servers. The only
external connections are Yahoo Finance, for market data (the ticker symbols
you enter are sent there), and Google Fonts, for the page fonts. Streamlit's
own usage statistics are turned off in `.streamlit/config.toml`.

The hosted app runs on Streamlit Community Cloud, so inputs entered there are
processed on its servers. The app stores nothing: results stay in the server's
memory for your session only. The platform keeps its own technical logs.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | [Streamlit](https://streamlit.io/) |
| Charts | [Plotly](https://plotly.com/python/) |
| Optimization | [PyPortfolioOpt](https://pyportfolioopt.readthedocs.io/) |
| Market Data | [yfinance](https://github.com/ranaroussi/yfinance) |
| PDF Export | [fpdf2](https://pyfpdf.github.io/fpdf2/) |

---

## Credits

- **Black-Litterman Model**: Fischer Black & Robert Litterman (1992)
- **Markowitz Model**: Harry Markowitz (1952)
- Mathematical implementation follows the [PyPortfolioOpt cookbook](https://github.com/robertmartin8/PyPortfolioOpt/tree/master/cookbook)

---

## License

Released under the [MIT License](LICENSE).
