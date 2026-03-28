"""
Black-Litterman Report Generator - PROFESSIONAL VERSION

Generates comprehensive PDF reports with methodology, visualizations, and analysis.
"""

import json
import os
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Import constants — supports both `python core/report.py` and `from core.report import ...`
try:
    from constants import (
        BENCHMARK_TICKER, HISTORICAL_PERIOD_YEARS,
        MIN_WEIGHT_THRESHOLD, RISK_FREE_RATE,
        TRADING_DAYS_PER_YEAR
    )
    from pdf_shared import (
        create_prior_chart, create_posterior_chart, create_comparison_chart,
        create_allocation_chart, create_historical_chart,
        add_methodology, add_disclaimers, add_chart_description,
        add_chart_to_pdf, add_historical_header, add_historical_metrics,
    )
except ImportError:
    from core.constants import (
        BENCHMARK_TICKER, HISTORICAL_PERIOD_YEARS,
        MIN_WEIGHT_THRESHOLD, RISK_FREE_RATE,
        TRADING_DAYS_PER_YEAR
    )
    from core.pdf_shared import (
        create_prior_chart, create_posterior_chart, create_comparison_chart,
        create_allocation_chart, create_historical_chart,
        add_methodology, add_disclaimers, add_chart_description,
        add_chart_to_pdf, add_historical_header, add_historical_metrics,
    )


def generate_report(output_filename="bl_portfolio_report.pdf", include_historical=False):
    """
    Generate comprehensive professional report from saved optimization results.
    """

    # Check if results file exists
    if not os.path.exists('bl_results.json'):
        print("=" * 70)
        print("ERROR: No saved results found")
        print("=" * 70)
        print("\nYou need to run the optimizer first:")
        print("  !python black_litterman_optimizer_clean.py")
        print("\nOR use quick_report() to generate from scratch:")
        print("  quick_report('MSFT, AMZN, GOOGL', 20000)")
        return None

    # Load saved results
    print("=" * 70)
    print("GENERATING PROFESSIONAL REPORT FROM SAVED RESULTS")
    print("=" * 70)
    print("\nLoading results from bl_results.json...")

    with open('bl_results.json', 'r') as f:
        results = json.load(f)

    # Extract data with safe access and validation
    required_keys = ['tickers', 'market_prior', 'ret_bl', 'weights',
                     'allocation', 'leftover', 'portfolio_value']
    missing_keys = [k for k in required_keys if k not in results]
    if missing_keys:
        print(f"ERROR: Results file is missing required fields: {missing_keys}")
        print("Please re-run opt.py to generate complete results.")
        return None

    tickers = results.get('tickers', [])
    market_prior = pd.Series(results.get('market_prior', {}))
    ret_bl = pd.Series(results.get('ret_bl', {}))
    viewdict = results.get('viewdict', {})
    weights = results.get('weights', {})
    allocation = results.get('allocation', {})
    leftover = results.get('leftover', 0)
    portfolio_value = results.get('portfolio_value', 0)

    # Extract analysis period (if available)
    analysis_start = results.get('analysis_start_date', None)
    analysis_end = results.get('analysis_end_date', None)

    # Use metrics from optimization (CONSISTENT with opt.py console output)
    print("Loading performance metrics from optimization...")
    performance_metrics = {
        'return': results.get('expected_return', 0) * 100,  # Convert to percentage
        'volatility': results.get('volatility', 0) * 100,    # Convert to percentage
        'sharpe': results.get('sharpe_ratio', 0)
    }

    # Validate that metrics exist
    if results.get('expected_return') is None:
        print("Warning: Performance metrics not found in saved results.")
        print("The report may show inconsistent values.")
        print("Please re-run opt.py to save complete metrics.")

    # Historical validation if requested
    historical_data = None
    if include_historical:
        print("Calculating historical validation...")
        historical_data = _calculate_historical_performance(tickers, weights, portfolio_value)

    # Generate comprehensive PDF with intercalated charts
    print("Generating comprehensive PDF report...")
    _generate_professional_pdf(
        tickers, market_prior, ret_bl, viewdict, weights, allocation,
        leftover, portfolio_value, performance_metrics,
        historical_data, output_filename, analysis_start, analysis_end
    )

    print(f"\nReport saved: {output_filename}")
    print("\nTo download in Colab:")
    print("  from google.colab import files")
    print(f"  files.download('{output_filename}')")
    print("=" * 70)

    return output_filename


def quick_report(tickers_str, portfolio_value=10000, output_filename="bl_portfolio_report.pdf"):
    """
    Generate report by re-calculating everything from scratch.
    """
    from pypfopt import BlackLittermanModel, risk_models, black_litterman
    from pypfopt import EfficientFrontier, objective_functions, DiscreteAllocation

    tickers = [t.strip().upper() for t in tickers_str.split(',')]

    print("=" * 70)
    print("GENERATING COMPREHENSIVE QUICK REPORT")
    print("=" * 70)
    print(f"\nTickers: {', '.join(tickers)}")
    print(f"Portfolio value: ${portfolio_value:,}\n")

    # Download data
    print("Downloading data...")
    ohlc = yf.download(tickers, period="max", progress=False)
    prices = ohlc["Close"]
    market_prices = yf.download(BENCHMARK_TICKER, period="max", progress=False)["Close"]

    # Get market caps
    mcaps = {}
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            mcaps[t] = stock.info["marketCap"]
        except Exception:
            mcaps[t] = 1e9

    # Calculate prior
    print("Calculating market prior...")
    S = risk_models.CovarianceShrinkage(prices).ledoit_wolf()
    delta = black_litterman.market_implied_risk_aversion(market_prices)
    market_prior = black_litterman.market_implied_prior_returns(mcaps, delta, S)

    # Run BL (market equilibrium - no views)
    print("Running Black-Litterman (market equilibrium)...")
    # Without views, posterior equals prior
    ret_bl = market_prior
    S_bl = S

    # Optimize
    print("Optimizing portfolio...")
    ef = EfficientFrontier(ret_bl, S_bl)
    ef.add_objective(objective_functions.L2_reg)
    ef.max_sharpe()
    weights = ef.clean_weights()

    # Performance metrics
    annual_return, annual_vol, sharpe = ef.portfolio_performance(verbose=False, risk_free_rate=RISK_FREE_RATE)
    performance_metrics = {
        'return': annual_return * 100,
        'volatility': annual_vol * 100,
        'sharpe': sharpe
    }

    # Discrete allocation
    print("Calculating allocation...")
    latest_prices = prices.iloc[-1]
    da = DiscreteAllocation(weights, latest_prices, total_portfolio_value=portfolio_value)
    allocation, leftover = da.lp_portfolio()

    # Extract analysis period from prices
    analysis_start = prices.index[0].strftime('%Y-%m-%d')
    analysis_end = prices.index[-1].strftime('%Y-%m-%d')

    # Generate PDF with intercalated charts
    print("Generating comprehensive PDF report...")
    _generate_professional_pdf(
        tickers, market_prior, ret_bl, {}, weights, allocation,
        leftover, portfolio_value, performance_metrics,
        None, output_filename, analysis_start, analysis_end
    )

    print(f"\nReport saved: {output_filename}")
    print("\nTo download in Colab:")
    print("  from google.colab import files")
    print(f"  files.download('{output_filename}')")
    print("=" * 70)

    return output_filename




def _calculate_historical_performance(tickers, weights, portfolio_value):
    """
    Calculate historical validation over past 5 years.

    Delegates to core.backtest (single source of truth for backtest calculations).
    """
    try:
        from backtest import download_and_run_backtest
    except ImportError:
        from core.backtest import download_and_run_backtest

    print(f"  Calculating historical performance for {len(tickers)} tickers...")
    bt_result = download_and_run_backtest(
        tickers=tickers,
        weights=weights,
        portfolio_value=portfolio_value,
        years=HISTORICAL_PERIOD_YEARS,
        benchmark=BENCHMARK_TICKER,
    )

    if bt_result is None:
        return None

    print(f"  Historical data calculated successfully")

    # Return dict format expected by _generate_professional_pdf
    result = bt_result.to_dict()
    result['period'] = f'{HISTORICAL_PERIOD_YEARS} years'
    return result


def _generate_professional_pdf(tickers, market_prior, ret_bl, viewdict, weights, allocation,
                                leftover, portfolio_value, metrics,
                                historical_data, output_file, analysis_start=None, analysis_end=None):
    """Generate comprehensive professional PDF report with intercalated charts."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # PAGE 1: Header, Executive Summary, Methodology, Market Prior + Chart
    _add_header(pdf, portfolio_value, analysis_start, analysis_end)
    _add_executive_summary(pdf, portfolio_value, len(tickers), metrics)
    add_methodology(pdf)
    _add_market_prior(pdf, market_prior)

    # Add Prior Returns Chart (shared: returns bytes, no file cleanup needed)
    print("  Creating Prior Returns chart...")
    add_chart_to_pdf(pdf, create_prior_chart(market_prior))
    add_chart_description(pdf, 'prior')

    # PAGE 2: User Views, Posterior Table, Posterior Chart, then Comparison as Summary
    if viewdict and len(viewdict) > 0:
        _add_user_views(pdf, viewdict)

        # Add Posterior comparison table
        _add_posterior_comparison(pdf, market_prior, ret_bl, viewdict)

        # Add Posterior Returns Chart
        print("  Creating Posterior Returns chart...")
        add_chart_to_pdf(pdf, create_posterior_chart(ret_bl))
        add_chart_description(pdf, 'posterior')

        # Add Comparison Chart LAST as a visual summary
        print("  Creating Comparison chart (visual summary)...")
        add_chart_to_pdf(pdf, create_comparison_chart(market_prior, ret_bl, viewdict))
        add_chart_description(pdf, 'comparison')
    else:
        # No views - use market equilibrium (simpler presentation)
        pdf.ln(3)
        pdf.set_font('helvetica', 'B', 12)
        pdf.cell(0, 7, 'Market Equilibrium Approach', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

        pdf.set_font('helvetica', '', 9)
        pdf.multi_cell(0, 5, "This portfolio uses pure market equilibrium without custom views. Expected returns are based solely on market capitalizations and historical risk characteristics. The optimization maximizes Sharpe ratio given these market-implied return expectations.")
        pdf.ln(5)

        # Note: No posterior or comparison charts since they would be identical to prior
        # This keeps the report clean and avoids redundancy

    # PAGE 3: Portfolio Allocation (chart first, then table)
    _add_allocation_title(pdf)
    print("  Creating Portfolio Allocation chart...")
    add_chart_to_pdf(pdf, create_allocation_chart(weights), width_scale=0.75)
    add_chart_description(pdf, 'allocation')
    _add_allocation_table(pdf, weights, allocation, portfolio_value, leftover, tickers)

    # PAGE 4: Risk Analysis, Historical Validation + Performance Chart
    _add_risk_analysis(pdf, weights, metrics)

    if historical_data:
        add_historical_header(pdf, historical_data)

        # Add Historical Performance Chart
        print("  Creating Historical Performance chart...")
        historical_chart_bytes = create_historical_chart(historical_data)
        if historical_chart_bytes:
            add_chart_to_pdf(pdf, historical_chart_bytes)
            add_chart_description(pdf, 'historical')

        add_historical_metrics(pdf, historical_data)

    # PAGE 5: Disclaimers
    pdf.add_page()
    add_disclaimers(pdf)

    pdf.output(output_file)




def _add_header(pdf, portfolio_value, analysis_start=None, analysis_end=None):
    """Add report header with optional logo (matches Project.ipynb style)."""
    # Try to add logo (gracefully handle missing file)
    logo_loaded = False
    for logo_file in ['PortfolioLab.png', 'Finance for all.png', 'logo.png']:
        try:
            pdf.image(logo_file, x=10, y=10, w=40)
            logo_loaded = True
            break
        except Exception:
            continue

    # Add title and generation timestamp
    pdf.set_font('helvetica', 'B', 20)
    pdf.set_y(25)
    pdf.cell(0, 10, 'Black-Litterman Portfolio Report', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('helvetica', '', 10)
    pdf.cell(0, 5, f'Portfolio Value: ${portfolio_value:,.0f}', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Add analysis period if available
    if analysis_start and analysis_end:
        pdf.cell(0, 5, f'Analysis Period: {analysis_start} to {analysis_end}', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(8)


def _add_executive_summary(pdf, portfolio_value, n_assets, metrics):
    """Add executive summary section."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Executive Summary', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    pdf.set_font('helvetica', '', 10)
    summary_text = f"This report presents an optimized portfolio allocation for ${portfolio_value:,.0f} across {n_assets} assets using the Black-Litterman model. The portfolio is designed to maximize risk-adjusted returns while incorporating market equilibrium and your investment views."
    pdf.multi_cell(0, 5, summary_text)
    pdf.ln(2)

    pdf.set_font('helvetica', 'B', 11)
    pdf.cell(0, 6, 'Expected Performance:', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('helvetica', '', 10)

    pdf.cell(50, 6, '  Annual Return:', new_x=XPos.RIGHT)
    pdf.cell(0, 6, f'{metrics["return"]:.2f}%', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.cell(50, 6, '  Volatility:', new_x=XPos.RIGHT)
    pdf.cell(0, 6, f'{metrics["volatility"]:.2f}%', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.cell(50, 6, '  Sharpe Ratio:', new_x=XPos.RIGHT)
    pdf.cell(0, 6, f'{metrics["sharpe"]:.2f}', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)




def _add_market_prior(pdf, market_prior):
    """Add market-implied prior returns."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Market-Implied Prior Returns', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    pdf.set_font('helvetica', '', 9)
    pdf.multi_cell(0, 5, "These are the expected returns implied by current market prices and capitalizations:")
    pdf.ln(1)

    pdf.set_font('helvetica', '', 9)
    sorted_prior = market_prior.sort_values(ascending=False)

    for ticker, ret in sorted_prior.items():
        pdf.cell(30, 5, f'  {ticker}:', new_x=XPos.RIGHT)
        pdf.cell(0, 5, f'{ret*100:.2f}%', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)


def _add_user_views(pdf, viewdict):
    """Add user investment views."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Your Investment Views', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    pdf.set_font('helvetica', '', 9)
    pdf.multi_cell(0, 5, "Your custom views on expected returns:")
    pdf.ln(1)

    for ticker, view in viewdict.items():
        pdf.cell(30, 5, f'  {ticker}:', new_x=XPos.RIGHT)
        pdf.cell(0, 5, f'{view*100:.2f}%', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)


def _add_posterior_comparison(pdf, market_prior, ret_bl, viewdict):
    """Add comparison table."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Posterior Returns (Blended)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.set_font('helvetica', '', 8)
    pdf.multi_cell(0, 5, "The Black-Litterman model blends market expectations with your views:")
    pdf.ln(2)

    # Calculate available width
    available_width = pdf.w - pdf.l_margin - pdf.r_margin

    # Table header with adjusted widths to fit page
    col_widths = [20, 28, 28, 28, 28]  # Total: 132 (safe)

    pdf.set_font('helvetica', 'B', 8)
    pdf.cell(col_widths[0], 5, 'Ticker', border=1, align='C', new_x=XPos.RIGHT)
    pdf.cell(col_widths[1], 5, 'Prior', border=1, align='C', new_x=XPos.RIGHT)
    pdf.cell(col_widths[2], 5, 'View', border=1, align='C', new_x=XPos.RIGHT)
    pdf.cell(col_widths[3], 5, 'Posterior', border=1, align='C', new_x=XPos.RIGHT)
    pdf.cell(col_widths[4], 5, 'Direction', border=1, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Table rows
    pdf.set_font('helvetica', '', 7)
    for ticker in market_prior.index:
        prior = market_prior[ticker] * 100
        view = viewdict.get(ticker, None)
        posterior = ret_bl[ticker] * 100

        if view is not None:
            view_str = f'{view*100:.1f}%'
            direction = 'Higher' if posterior > prior else ('Lower' if posterior < prior else 'Same')
        else:
            view_str = 'N/A'
            direction = '-'

        pdf.cell(col_widths[0], 5, ticker, border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[1], 5, f'{prior:.1f}%', border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[2], 5, view_str, border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[3], 5, f'{posterior:.1f}%', border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[4], 5, direction, border=1, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)


def _add_allocation_title(pdf):
    """Add portfolio allocation section title only (chart is placed after this)."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Recommended Portfolio Allocation', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)


def _add_allocation_table(pdf, weights, allocation, portfolio_value, leftover, tickers):
    """Add allocation intro text, weights/shares table, and cash remaining."""
    pdf.set_font('helvetica', '', 9)
    pdf.multi_cell(0, 5, "Optimal weights and discrete share allocation:")
    pdf.ln(1)

    # Calculate safe column widths
    col_widths = [22, 22, 33, 22]  # Total: 99 (safe)

    # Table header
    pdf.set_font('helvetica', 'B', 9)
    pdf.cell(col_widths[0], 6, 'Ticker', border=1, align='C', new_x=XPos.RIGHT)
    pdf.cell(col_widths[1], 6, 'Weight', border=1, align='C', new_x=XPos.RIGHT)
    pdf.cell(col_widths[2], 6, 'Amount', border=1, align='C', new_x=XPos.RIGHT)
    pdf.cell(col_widths[3], 6, 'Shares', border=1, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Table rows
    pdf.set_font('helvetica', '', 8)
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)

    for ticker, weight in sorted_weights:
        if weight > MIN_WEIGHT_THRESHOLD:
            amount = weight * portfolio_value
            shares = allocation.get(ticker, 0)

            pdf.cell(col_widths[0], 6, ticker, border=1, align='C', new_x=XPos.RIGHT)
            pdf.cell(col_widths[1], 6, f'{weight*100:.1f}%', border=1, align='C', new_x=XPos.RIGHT)
            pdf.cell(col_widths[2], 6, f'${amount:,.0f}', border=1, align='C', new_x=XPos.RIGHT)
            pdf.cell(col_widths[3], 6, str(shares), border=1, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(1)
    pdf.set_font('helvetica', 'B', 9)
    pdf.cell(0, 6, f'Cash Remaining: ${leftover:.2f}', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)


def _add_risk_analysis(pdf, weights, metrics):
    """Add risk analysis section."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Risk Analysis', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    pdf.set_font('helvetica', '', 9)

    # Diversification
    n_holdings = sum(1 for w in weights.values() if w > MIN_WEIGHT_THRESHOLD)
    max_weight = max(weights.values())

    pdf.cell(0, 5, f'Number of Holdings: {n_holdings}', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f'Largest Position: {max_weight*100:.1f}%', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f'Expected Volatility: {metrics["volatility"]:.2f}%', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f'Sharpe Ratio: {metrics["sharpe"]:.2f}', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)







if __name__ == "__main__":
    print("=" * 70)
    print("BLACK-LITTERMAN PROFESSIONAL REPORT GENERATOR")
    print("=" * 70)

    # Check for logo
    logo_found = False
    for possible_path in ['PortfolioLab.png', 'Finance for all.png', 'logo.png']:
        if os.path.exists(possible_path):
            print(f"\nLogo found: {possible_path}")
            logo_found = True
            break

    if not logo_found:
        print("\nNote: No logo found. Place 'Finance_for_all.png' in the same directory to add it.")

    # Check if we have saved results
    if os.path.exists('bl_results.json'):
        print("\nFound saved results from optimizer")
        print("Generating comprehensive professional report...\n")

        # Ask about historical validation
        try:
            response = input("Include historical validation? (y/n, default n): ").strip().lower()
            include_hist = response in ['y', 'yes']
        except Exception:
            include_hist = False

        generate_report(include_historical=include_hist)
    else:
        print("\nNo saved results found (bl_results.json)")
        print("Generating quick comprehensive report...\n")

        # Ask for tickers
        print("Enter tickers (comma-separated): ", end="")
        tickers_input = input().strip()

        if not tickers_input:
            print("Using example: MSFT, AMZN, GOOGL, AAPL, TSLA")
            tickers_input = "MSFT, AMZN, GOOGL, AAPL, TSLA"

        # Ask for portfolio value
        print("Portfolio value in USD (default 10000): ", end="")
        value_input = input().strip()

        if not value_input:
            portfolio_value = 10000
        else:
            try:
                portfolio_value = float(value_input)
            except (ValueError, TypeError):
                portfolio_value = 10000

        print("\n")
        quick_report(tickers_input, portfolio_value)