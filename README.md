# PortfolioLab

**PortfolioLab** is an open-source financial platform built with Streamlit. It provides professional-grade tools for stock exploration, portfolio construction, and performance analysis — all running locally to keep your financial data private.

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
- **Markowitz (Mean-Variance)**: Optimize for Max Sharpe, Min Variance, Target Risk, or Target Return
- **Black-Litterman**: Bayesian optimization combining market equilibrium with custom investor views
- Efficient frontier visualization, historical backtesting, and correlation analysis
- Downloadable PDF reports with full breakdown

---

## Requirements

- **Python 3.12** (Python 3.13 is not yet supported by PyPortfolioOpt)
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
│   ├── report.py             # PDF report generation
│   └── constants.py          # Centralized constants
├── utils/                    # Streamlit integration layer
│   ├── styles.py             # Design system & CSS
│   ├── visualizations.py     # Plotly interactive charts
│   ├── optimizer_wrapper.py  # UI ↔ core bridge
│   ├── pdf_generator.py      # Web PDF export
│   └── session_manager.py    # Streamlit session state
├── tests/                    # pytest test suite
├── static/                   # Images and PWA assets
└── assets/                   # Logo
```

---

## Running Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -v
```

---

## Privacy

All calculations run **locally** on your machine. No portfolio data or investment views are sent to external servers. The only external connection is to Yahoo Finance to fetch historical price data.

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
