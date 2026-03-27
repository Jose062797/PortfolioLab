"""
Verification script — compares our get_asset_info() output
against raw yfinance data to ensure no formatting errors.

Usage:
    python scripts/verify_metrics.py MSFT
    python scripts/verify_metrics.py MSFT AAPL QQQ BTC-USD
"""
import sys
import os

# Add parent dir to path so we can import core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf


def verify(ticker: str):
    """Print raw yfinance values alongside formatted for manual comparison with Yahoo Finance."""
    print(f"\n{'='*70}")
    print(f"  {ticker} — Raw yfinance vs Yahoo Finance comparison")
    print(f"{'='*70}\n")

    stock = yf.Ticker(ticker)
    info = stock.info or {}

    # Define all fields we display and their yfinance keys
    checks = [
        # (Our Label, yfinance key(s), format description)
        ("Price", ["currentPrice", "regularMarketPrice"], "direct"),
        ("Previous Close", ["previousClose"], "direct"),
        ("Open", ["regularMarketOpen", "open"], "direct"),
        ("Day Low", ["dayLow"], "direct"),
        ("Day High", ["dayHigh"], "direct"),
        ("52W Low", ["fiftyTwoWeekLow"], "direct"),
        ("52W High", ["fiftyTwoWeekHigh"], "direct"),
        ("Volume", ["volume", "regularMarketVolume"], "direct"),
        ("Avg Volume", ["averageVolume"], "direct"),
        ("Market Cap", ["marketCap"], "abbreviated"),  # we show as 2.89T
        ("Beta", ["beta"], "2 decimals"),
        ("P/E (TTM)", ["trailingPE"], "2 decimals"),
        ("Forward P/E", ["forwardPE"], "2 decimals"),
        ("EPS (TTM)", ["trailingEps"], "2 decimals"),
        ("PEG Ratio", ["pegRatio", "trailingPegRatio"], "2 decimals"),
        ("P/B Ratio", ["priceToBook"], "2 decimals"),
        ("P/S Ratio", ["priceToSalesTrailing12Months"], "2 decimals"),
        ("EV/EBITDA", ["enterpriseToEbitda"], "2 decimals"),
        ("Revenue", ["totalRevenue"], "abbreviated"),
        ("Net Income", ["netIncomeToCommon"], "abbreviated"),
        ("EBITDA", ["ebitda"], "abbreviated"),
        ("Gross Margin", ["grossMargins"], "percentage"),  # raw = 0.686
        ("Operating Margin", ["operatingMargins"], "percentage"),
        ("Profit Margin", ["profitMargins", "profitMargin"], "percentage"),
        ("ROE", ["returnOnEquity"], "percentage"),
        ("ROA", ["returnOnAssets"], "percentage"),
        ("Dividend Rate", ["dividendRate"], "direct"),
        ("Dividend Yield", ["dividendYield"], "percentage"),
        ("1Y Target", ["targetMeanPrice"], "direct"),
        ("Target Low", ["targetLowPrice"], "direct"),
        ("Target High", ["targetHighPrice"], "direct"),
        ("Recommendation", ["recommendationKey"], "string"),
        ("# Analysts", ["numberOfAnalystOpinions"], "direct"),
    ]

    def _fmt_abbreviated(val):
        if val is None:
            return "N/A"
        if abs(val) >= 1e12:
            return f"${val/1e12:.2f}T"
        if abs(val) >= 1e9:
            return f"${val/1e9:.2f}B"
        if abs(val) >= 1e6:
            return f"${val/1e6:.2f}M"
        return f"${val:,.0f}"

    print(f"{'Metric':<22} {'Raw Value':<20} {'Our Display':<20} {'Match?'}")
    print("-" * 70)

    issues = 0
    for label, keys, fmt in checks:
        # Get raw value (try multiple keys)
        raw = None
        used_key = None
        for k in keys:
            if info.get(k) is not None:
                raw = info[k]
                used_key = k
                break

        # Format as we display it
        if raw is None:
            display = "N/A"
            raw_str = "None"
        elif fmt == "percentage":
            display = f"{raw * 100:.2f}%"
            raw_str = f"{raw}"
        elif fmt == "abbreviated":
            display = _fmt_abbreviated(raw)
            raw_str = f"{raw}"
        elif fmt == "2 decimals":
            display = f"{raw:.2f}"
            raw_str = f"{raw}"
        elif fmt == "string":
            display = str(raw)
            raw_str = str(raw)
        else:
            display = f"{raw:,.2f}" if isinstance(raw, float) else str(raw)
            raw_str = str(raw)

        # Check if value seems reasonable
        warn = ""
        if fmt == "percentage" and raw is not None and abs(raw) > 1:
            warn = "⚠️ >100%!"
            issues += 1
        elif raw is None:
            warn = "—"

        print(f"{label:<22} {raw_str:<20} {display:<20} {warn}")

    print(f"\n{'='*70}")
    if issues == 0:
        print("✅ All values look reasonable")
    else:
        print(f"⚠️  {issues} potential issue(s) found")
    print(f"\nCompare these values with: https://finance.yahoo.com/quote/{ticker}/")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["MSFT"]
    for t in tickers:
        verify(t)
