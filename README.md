# PortfolioLab

[![Tests](https://github.com/Jose062797/PortfolioLab/actions/workflows/tests.yml/badge.svg)](https://github.com/Jose062797/PortfolioLab/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.14-blue.svg)](https://www.python.org/)

**PortfolioLab** is an open-source financial platform built with Streamlit. It provides professional-grade tools for stock exploration, portfolio construction, and performance analysis.

### 🚀 [Try the live demo](https://portfoliolab-qzrhvh2p5ls7xqhyx38smv.streamlit.app/)

> For educational and informational purposes only — not investment advice.

---

## Features

### 📊 Stocks
Interactive dashboard to explore any asset available on Yahoo Finance (stocks, ETFs, indices, crypto).
- Real-time pricing, candlestick and line charts with volume
- Key statistics: price, market cap, volume, 52-week range
- Revenue vs. earnings quarterly breakdown
- Period returns (1D, 5D, 1M, 6M, YTD, 1Y, 5Y) benchmarked against S&P 500

### 📈 Portfolio Optimizer
Advanced portfolio construction engine supporting two mathematical models:
- **Markowitz (Mean-Variance)**: Optimize for Max Sharpe, Min Variance, Target Risk, or Target Return — with a choice of expected-returns estimator (CAPM or historical mean, for non-equity assets)
- **Black-Litterman**: Bayesian optimization combining market equilibrium with custom investor views
- Efficient frontier visualization, historical backtesting, and correlation analysis
- Overlapping-holdings detection (flags near-perfectly correlated assets, e.g. an ETF held alongside its own constituents)
- Downloadable PDF reports with full breakdown

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
├── streamlit_app.py          # Landing page & entry point
├── pages/
│   ├── 1_Stocks.py           # Stock/asset exploration tool
│   ├── 2_Portfolio.py        # Portfolio optimization tool
│   └── 3_About.py            # Documentation & methodology
├── core/                     # Framework-independent business logic
│   ├── opt_engine.py         # Math engine (Markowitz & Black-Litterman)
│   ├── backtest.py           # Historical simulation
│   ├── data_provider.py      # yfinance data layer
│   ├── pdf_shared.py         # Shared PDF chart builders
│   └── constants.py          # Centralized constants
├── utils/                    # Streamlit integration layer
│   ├── styles.py             # Design system & CSS
│   ├── visualizations.py     # Plotly interactive charts
│   ├── optimizer_wrapper.py  # UI ↔ core bridge
│   ├── pdf_generator.py      # Web PDF export
│   └── session_manager.py    # Streamlit session state
├── tests/                    # pytest test suite (parity, regression, edge cases)
├── static/                   # Images and PWA assets
├── assets/                   # Logo
└── .github/workflows/        # CI (pytest on Python 3.12 & 3.14)
```

---

## Running Tests

```powershell
pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests\ -v
```

The suite (75+ tests) runs fully offline against synthetic fixtures and covers:
mathematical parity with raw PyPortfolioOpt, frozen numeric regression
snapshots, numerical edge cases, data-layer failure modes, input validation,
PDF/visualization outputs, and backtest conventions. It also runs automatically
on every push via GitHub Actions (Python 3.12 and 3.14).

---

## Privacy

When you **run PortfolioLab locally**, all calculations happen on your machine:
no portfolio data or investment views are sent to external servers, and the
only external connection is to Yahoo Finance for historical price data.

The hosted demo runs on Streamlit Community Cloud, so inputs entered there are
processed on Streamlit's servers (nothing is persisted by the app — results
live only in the browser session).

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
- Mathematical implementation follows the [PyPortfolioOpt cookbook](https://pyportfolioopt.readthedocs.io/en/latest/Cookbook.html)

---

## License

Released under the [MIT License](LICENSE).
