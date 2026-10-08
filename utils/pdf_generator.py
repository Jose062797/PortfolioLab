"""
PDF Report Generator for Black-Litterman Portfolio Optimizer
Generates comprehensive professional PDF reports from Streamlit results.

Structure mirrors the web page tabs:
  Page 1: Cover + Metric Cards + Executive Summary + Methodology
  Page 2: Allocation (pie chart first, then weights table)
  Page 3: Returns Analysis (comparison chart + numerical table)
  Page 4: Historical Performance (chart "All" + backtest metrics)
  Page 5: Correlation (heatmap)
  Page 6: Detailed Breakdown (Portfolio Summary + Discrete Allocation)
  Page 7: Disclaimers
"""

import os
import logging
from datetime import datetime

import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from core.pdf_shared import (
    create_comparison_chart,
    create_allocation_chart,
    create_correlation_heatmap,
    create_historical_chart,
    add_methodology,
    add_disclaimers,
    add_chart_description,
    describe_objective,
    add_chart_to_pdf,
    add_historical_header,
    add_historical_metrics,
)
from core.constants import (
    CALENDAR_DAYS_PER_YEAR, MIN_WEIGHT_THRESHOLD, OBJECTIVE_LABELS, SHRINKAGE_NOTE_THRESHOLD,
    goal_text, risk_free_text,
)
from utils.text import fmt_price

logger = logging.getLogger(__name__)


class PortfolioPDFReport(FPDF):
    """Custom PDF class for portfolio reports with header/footer."""

    def __init__(self, model_type='Black-Litterman'):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self._model_type = model_type

    def header(self):
        """Add header to each page (except first page)."""
        if self.page_no() > 1:
            self.set_font('helvetica', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 5, f'{self._model_type} Portfolio Report',
                      align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(3)
            self.set_text_color(0, 0, 0)

    def footer(self):
        """Add footer with page number."""
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
        self.set_text_color(0, 0, 0)


def build_report_pdf(result_data, logo_path=None) -> bytes:
    """
    The Portfolio page's whole report: the backtest (if the result does not
    carry one yet), then the PDF. The page hands this to st.download_button
    as a callable, so it runs only when someone clicks Download, not on
    every rerun of the results page (it was the page's heaviest work).
    """
    from utils.optimizer_wrapper import run_backtest

    if result_data.get('historical_data') is None:
        try:
            result_data['historical_data'] = run_backtest(
                result_data, date_range=result_data.get('date_range')) or None
        except Exception:
            logger.exception("Backtest for the PDF failed")
            result_data['historical_data'] = None
    return bytes(generate_portfolio_pdf(result_data, logo_path=logo_path))


def generate_portfolio_pdf(result_data, logo_path=None):
    """
    Generate comprehensive PDF report from optimization results.
    Structure mirrors the web page tabs.

    Args:
        result_data: Dictionary containing all optimization results from Streamlit
        logo_path: Optional path to logo image

    Returns:
        bytes: PDF file as bytes buffer
    """
    model_type = result_data.get('model_type', 'Black-Litterman')
    obj_function = result_data.get('obj_function', 'Max Sharpe')
    pdf = PortfolioPDFReport(model_type=model_type)
    pdf.add_page()

    # Extract data from results
    tickers = result_data.get('tickers', [])
    portfolio_value = result_data.get('portfolio_value', 0)
    market_prior = pd.Series(result_data.get('market_prior', {}))
    posterior = pd.Series(result_data.get('posterior', {}))
    views = result_data.get('viewdict', {})
    weights = result_data.get('weights', {})
    allocation = result_data.get('allocation', {})
    leftover = result_data.get('leftover', 0)

    # Performance metrics
    metrics = result_data.get('metrics', {})
    expected_return = metrics.get('return', result_data.get('expected_return', 0))
    volatility = metrics.get('volatility', result_data.get('volatility', 0))
    sharpe_ratio = metrics.get('sharpe', result_data.get('sharpe_ratio', 0))

    # Historical and covariance data
    historical_data = result_data.get('historical_data', None)
    covariance = result_data.get('covariance_matrix', None)

    # The prices the shares were bought at: each asset's last close,
    # forward-filled like core/opt_engine.calculate_allocation (the plain last
    # row is NaN for stocks when crypto adds a weekend date).
    latest_prices = dict(result_data.get('latest_prices') or {})
    prices_clean_dict = result_data.get('prices_clean', {})
    if not latest_prices and prices_clean_dict:
        last_row = pd.DataFrame.from_dict(prices_clean_dict, orient='index').sort_index().ffill().iloc[-1]
        latest_prices = {t: float(p) for t, p in last_row.items() if pd.notna(p)}

    # Periods: every downloaded row (estimation, share prices) and the
    # backtest's common dates (see utils/optimizer_wrapper.run_optimization)
    full_data_range = result_data.get('full_data_range') or result_data.get('date_range')
    full_start, full_end = full_data_range if full_data_range else ('N/A', 'N/A')
    backtest_range = result_data.get('backtest_range')

    num_assets = sum(1 for w in weights.values() if w > MIN_WEIGHT_THRESHOLD)
    # The backtest period is shown only when the report has the backtest: it
    # used to print on the cover even when the Historical page was missing
    # (audit B3-06)
    shown_backtest_range = backtest_range if historical_data else None

    # ── PAGE 1: Cover + Executive Summary + Metric Cards + Methodology ──
    _add_cover_page(pdf, portfolio_value, full_start, full_end, shown_backtest_range,
                    logo_path, model_type, obj_function)
    _add_executive_summary(pdf, portfolio_value, num_assets, result_data)
    _add_metric_cards(pdf, expected_return, volatility, sharpe_ratio,
                      portfolio_value, num_assets)
    add_methodology(pdf, result_data)
    # The same data notes as the web's notes box that change how to read
    # the figures (audit B2-01, F1-02)
    notes = result_data.get('data_notes') or {}
    if (notes.get('shrinkage') or 0) >= SHRINKAGE_NOTE_THRESHOLD:
        _add_note(pdf, f"Little data for the risk model: with {notes.get('common_days', 'few')} days of "
                       f"prices in common, the Ledoit-Wolf risk model leans {notes['shrinkage']:.0%} on "
                       "its neutral starting point (every asset equally risky, none correlated), so "
                       "the weights drift toward equal shares and the correlations toward zero.")
    if notes.get('trading_days_per_year') == CALENDAR_DAYS_PER_YEAR:
        _add_note(pdf, "Every asset trades every day, so the annual figures use 365 days a year, "
                       "not the 252 of stock markets.")

    # Optional sections never sink the whole report: a failure is logged and
    # leaves a line in the PDF, where it used to vanish or, uncaught, stop the
    # download with Streamlit's generic error (audit B3-07, B3-12).

    # ── PAGE 2: Allocation (Tab 1) — chart first, then table ──
    pdf.add_page()
    _add_allocation_title(pdf)
    try:
        add_chart_to_pdf(pdf, create_allocation_chart(weights), width_scale=0.75)
        add_chart_description(pdf, 'allocation', result_data)
    except Exception:
        logger.exception("PDF allocation chart failed")
        _add_note(pdf, "The allocation chart could not be drawn for this run; the table below has every weight.")
    _add_allocation_table(pdf, weights, allocation, portfolio_value, latest_prices)

    # ── PAGE 3: Returns Analysis (Tab 2) — only for Black-Litterman ──
    if model_type != "Markowitz" and len(market_prior) > 0:
        views_detail = result_data.get('views_detail', {})
        pdf.add_page()
        try:
            _add_returns_analysis(pdf, market_prior, posterior, views, views_detail)
        except Exception:
            logger.exception("PDF returns analysis failed")
            _add_note(pdf, "The returns analysis could not be drawn for this run.")

    # ── PAGE 4: Historical Performance (Tab 3) ──
    if historical_data:
        pdf.add_page()
        logger.info("Historical data available, adding performance section")
        try:
            add_historical_header(pdf, historical_data)
            hist_chart = create_historical_chart(historical_data, model_type)
            if hist_chart:
                add_chart_to_pdf(pdf, hist_chart)
                add_chart_description(pdf, 'historical')
            else:
                _add_note(pdf, "The historical chart could not be drawn for this run.")
            add_historical_metrics(pdf, historical_data, model_type)
        except Exception:
            logger.exception("PDF historical performance failed")
            _add_note(pdf, "The historical performance could not be completed for this run.")
    else:
        _add_note(pdf, "Historical performance: not available for this run. The backtest needs at "
                       "least 20 days on which every asset and SPY have a price.")

    # ── PAGE 5: Correlation (Tab 4) ──
    if covariance is not None:
        # Labels in the matrix's own order (see optimizer_wrapper)
        corr_chart = create_correlation_heatmap(
            covariance, result_data.get('covariance_tickers') or tickers)
        if corr_chart:
            pdf.add_page()
            pdf.set_font('helvetica', 'B', 14)
            pdf.cell(0, 8, 'Correlation Analysis',
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)
            add_chart_to_pdf(pdf, corr_chart)
            add_chart_description(pdf, 'correlation')
        else:
            _add_note(pdf, "The correlation matrix could not be drawn for this run.")

    # ── PAGE 6: Detailed Breakdown (Tab 5) ──
    pdf.add_page()
    _add_detailed_breakdown(pdf, portfolio_value, leftover, num_assets,
                            full_start, full_end, shown_backtest_range, result_data)

    # ── PAGE 7: Disclaimers ──
    pdf.add_page()
    add_disclaimers(pdf, model_type)

    # Return PDF as bytes
    pdf_output = pdf.output()
    if isinstance(pdf_output, bytearray):
        return bytes(pdf_output)
    return pdf_output


# ═══════════════════════════════════════════════════════════════════
#  PDF Sections
# ═══════════════════════════════════════════════════════════════════

def _add_note(pdf, text):
    """A short grey line where a section is missing or could not be drawn."""
    pdf.set_font('helvetica', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 5, text,
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)


def _add_cover_page(pdf, portfolio_value, full_start, full_end, backtest_range,
                    logo_path, model_type='Black-Litterman', obj_function='Max Sharpe'):
    """Add cover page with title and metadata."""
    if logo_path and os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=10, y=10, w=40)
        except Exception as e:
            logger.warning("Could not add logo to PDF cover: %s", e)

    pdf.set_font('helvetica', 'B', 24)
    pdf.set_y(40)
    pdf.cell(0, 12, model_type, align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    # Show the goal for Markowitz, in the words the app uses
    if model_type == 'Markowitz':
        pdf.set_font('helvetica', '', 16)
        pdf.cell(0, 10, f'Goal: {OBJECTIVE_LABELS.get(obj_function, obj_function)}', align='C',
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('helvetica', 'B', 24)
    pdf.cell(0, 12, 'Portfolio Report', align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(15)

    pdf.set_font('helvetica', '', 11)
    # The web's words throughout the report (audit F1-16)
    pdf.cell(0, 6, f'Budget: ${portfolio_value:,.0f}',
             align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
             align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if full_start != 'N/A':
        pdf.cell(0, 6, f'Price data: {full_start} to {full_end}',
                 align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if backtest_range:
        pdf.cell(0, 6, f'Backtest period: {backtest_range[0]} to {backtest_range[1]}',
                 align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(10)


def _add_metric_cards(pdf, expected_return, volatility, sharpe_ratio,
                      portfolio_value, num_assets):
    """Add metric cards row (no title, data speaks for itself)."""
    pdf.ln(3)

    # Draw a bordered row of 5 metric cards
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    card_width = available_width / 5
    card_height = 16
    start_x = pdf.l_margin
    start_y = pdf.get_y()

    labels = ['Expected Return', 'Volatility', 'Sharpe Ratio', 'Budget', 'Assets']
    values = [
        f'{expected_return * 100:.2f}%',
        f'{volatility * 100:.2f}%',
        f'{sharpe_ratio:.3f}',
        f'${portfolio_value:,.0f}',
        str(num_assets),
    ]

    for i in range(5):
        x = start_x + i * card_width
        # Card border
        pdf.set_draw_color(200, 200, 200)
        pdf.rect(x, start_y, card_width, card_height)

        # Label
        pdf.set_xy(x, start_y + 1)
        pdf.set_font('helvetica', '', 7)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(card_width, 5, labels[i], align='C')

        # Value
        pdf.set_xy(x, start_y + 7)
        pdf.set_font('helvetica', 'B', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(card_width, 7, values[i], align='C')

    pdf.set_text_color(0, 0, 0)
    pdf.set_y(start_y + card_height + 5)

    # Footnote, in the web caption's terms: these are the model's estimates;
    # the Historical Performance page has the backtest's own figures
    pdf.set_font('helvetica', 'I', 7)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 4,
             "The model's annual estimates for these weights (3% risk-free rate), not forecasts. "
             'Historical Performance shows what they would have earned.',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)


def _add_executive_summary(pdf, portfolio_value, n_assets, result_data):
    """Add executive summary paragraph: what this run optimized, in one paragraph."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Executive Summary',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.set_font('helvetica', '', 10)
    available_width = pdf.w - pdf.l_margin - pdf.r_margin

    model_type = result_data.get('model_type', 'Black-Litterman')
    obj_function = result_data.get('obj_function', 'Max Sharpe')
    gamma = result_data.get('l2_gamma')

    if model_type == "Markowitz":
        obj_desc = describe_objective(obj_function, result_data.get('target_volatility'),
                                      result_data.get('target_return'))
        goal = OBJECTIVE_LABELS.get(obj_function, obj_function)
        summary_text = (
            f"This report presents an optimized portfolio allocation for "
            f"${portfolio_value:,.0f} across {n_assets} assets using "
            f"Mean-Variance Optimization (Markowitz) with the goal "
            f"\"{goal}\" ({obj_function}), which {obj_desc}."
        )
    else:
        views_part = ("your views" if result_data.get('viewdict')
                      else "no views, so the market equilibrium alone")
        # With gamma 0 the engine skips L2 (audit F1-07)
        penalty_part = (f"with an L2 penalty (gamma = {gamma:.1f}) that spreads the weights"
                        if gamma else "with no L2 penalty (gamma = 0)")
        summary_text = (
            f"This report presents an optimized portfolio allocation for "
            f"${portfolio_value:,.0f} across {n_assets} assets using the "
            f"Black-Litterman model. It blends the returns implied by market "
            f"capitalizations with {views_part}, then looks for the highest "
            f"expected Sharpe ratio (3% risk-free rate) {penalty_part}."
        )

    pdf.multi_cell(available_width, 5, summary_text)
    pdf.ln(2)


# ── Tab 1: Allocation ──

def _add_allocation_title(pdf):
    """Add portfolio allocation section title only (chart is placed after this)."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Portfolio Allocation',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)


def _add_allocation_table(pdf, weights, allocation, portfolio_value, latest_prices=None):
    """Add intro text and allocation table, with the web page's columns:
    Asset | Weight | Shares | Price | Target Value | Actual Value.

    Target Value = weight x budget (before rounding to whole shares);
    Actual Value = shares x the price they were bought at.
    """
    pdf.set_font('helvetica', '', 9)
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.multi_cell(available_width, 5,
                   "Optimal portfolio weights and discrete share allocation:")
    pdf.ln(2)

    prices = latest_prices or {}
    headers = ['Asset', 'Weight', 'Shares', 'Price', 'Target Value', 'Actual Value']
    col_widths = [22, 22, 18, 28, 32, 32]
    pdf.set_font('helvetica', 'B', 9)
    for i, (header, width) in enumerate(zip(headers, col_widths)):
        last = i == len(headers) - 1
        pdf.cell(width, 6, header, border=1, align='C',
                 new_x=XPos.LMARGIN if last else XPos.RIGHT,
                 new_y=YPos.NEXT if last else YPos.TOP)

    pdf.set_font('helvetica', '', 8)
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)

    for ticker, weight in sorted_weights:
        if weight > MIN_WEIGHT_THRESHOLD:
            shares = allocation.get(ticker, 0)
            price = prices.get(ticker)
            cells = [
                ticker,
                f'{weight*100:.2f}%',
                str(shares),
                f'${fmt_price(price)}' if price else 'N/A',
                f'${weight * portfolio_value:,.2f}',
                f'${shares * price:,.2f}' if price else 'N/A',
            ]
            for i, (text, width) in enumerate(zip(cells, col_widths)):
                last = i == len(cells) - 1
                pdf.cell(width, 6, text, border=1, align='C',
                         new_x=XPos.LMARGIN if last else XPos.RIGHT,
                         new_y=YPos.NEXT if last else YPos.TOP)

    pdf.ln(5)


# ── Tab 2: Returns Analysis ──

def _add_returns_analysis(pdf, market_prior, posterior, views, views_detail=None):
    """Add returns analysis: comparison chart + numerical table (matching web Tab 2)."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Returns Analysis',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    # Comparison chart (Prior vs Posterior vs Views)
    add_chart_to_pdf(pdf, create_comparison_chart(market_prior, posterior, views))
    add_chart_description(pdf, 'comparison')

    # Numerical comparison table with view intervals
    pdf.set_font('helvetica', 'B', 11)
    pdf.cell(0, 7, 'Numerical Comparison',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    has_views = views and len(views) > 0
    if has_views:
        col_widths = [18, 22, 22, 20, 20, 22]
        pdf.set_font('helvetica', 'B', 7)
        pdf.cell(col_widths[0], 5, 'Asset', border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[1], 5, 'Prior', border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[2], 5, 'View', border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[3], 5, 'Low', border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[4], 5, 'High', border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[5], 5, 'Posterior', border=1, align='C',
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        col_widths = [25, 35, 35]
        pdf.set_font('helvetica', 'B', 7)
        pdf.cell(col_widths[0], 5, 'Asset', border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[1], 5, 'Prior', border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[2], 5, 'Posterior', border=1, align='C',
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('helvetica', '', 7)
    for ticker in market_prior.index:
        prior_val = market_prior[ticker] * 100
        post_val = posterior[ticker] * 100

        pdf.cell(col_widths[0], 5, ticker, border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[1], 5, f'{prior_val:.2f}%', border=1, align='C', new_x=XPos.RIGHT)

        if has_views:
            # View value
            if ticker in views:
                view_data = views[ticker]
                view_val = (view_data.get('expected_return', view_data.get('expected', 0))
                            if isinstance(view_data, dict) else view_data) * 100
                view_str = f'{view_val:.2f}%'
            else:
                view_str = 'N/A'
            pdf.cell(col_widths[2], 5, view_str, border=1, align='C', new_x=XPos.RIGHT)

            # Lower / Upper from views_detail
            detail = views_detail.get(ticker) if views_detail else None
            if detail and isinstance(detail, dict):
                lower_str = f'{detail.get("lower", 0) * 100:.2f}%'
                upper_str = f'{detail.get("upper", 0) * 100:.2f}%'
            else:
                lower_str = 'N/A'
                upper_str = 'N/A'
            pdf.cell(col_widths[3], 5, lower_str, border=1, align='C', new_x=XPos.RIGHT)
            pdf.cell(col_widths[4], 5, upper_str, border=1, align='C', new_x=XPos.RIGHT)

        pdf.cell(col_widths[-1], 5, f'{post_val:.2f}%', border=1, align='C',
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if not has_views:
        pdf.ln(1)
        pdf.set_font('helvetica', 'I', 8)
        pdf.cell(0, 5, 'No custom views - using pure market equilibrium.',
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(5)


# ── Tab 5: Detailed Breakdown ──

def _add_detailed_breakdown(pdf, portfolio_value, leftover, num_assets,
                            full_start, full_end, backtest_range, result_data):
    """Add detailed breakdown: Portfolio Summary and Model Settings (matching web Tab 5)."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Detailed Breakdown',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # ── Portfolio Summary ──
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 7, 'Portfolio Summary',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    # The web Details tab's rows and words (audit F1-16)
    pdf.set_font('helvetica', '', 10)
    pdf.cell(50, 6, 'Budget:', new_x=XPos.RIGHT)
    pdf.cell(0, 6, f'${portfolio_value:,.2f}',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.cell(50, 6, 'Assets:', new_x=XPos.RIGHT)
    pdf.cell(0, 6, str(num_assets),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.cell(50, 6, 'Cash left over:', new_x=XPos.RIGHT)
    pdf.cell(0, 6, f'${leftover:,.2f}',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if full_start != 'N/A':
        pdf.cell(50, 6, 'Price data:', new_x=XPos.RIGHT)
        bl_clause = ("; the risk aversion uses SPY's whole history"
                     if result_data.get('model_type') == 'Black-Litterman' else "")
        pdf.multi_cell(0, 6, f'{full_start} to {full_end} (dates with a price for every asset: '
                             f'expected returns, covariance and share prices{bl_clause})',
                       new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(50, 6, 'Backtest period:', new_x=XPos.RIGHT)
    if backtest_range:
        pdf.multi_cell(0, 6, f'{backtest_range[0]} to {backtest_range[1]} (days with a price for every asset and SPY)',
                       new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        pdf.cell(0, 6, 'not available for this run',
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Model Settings (the web page's rows) ──
    pdf.ln(4)
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 7, 'Model Settings', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_font('helvetica', '', 10)

    model_type = result_data.get('model_type', 'Black-Litterman')
    objective = result_data.get('obj_function', 'Max Sharpe')
    goal = (f"{goal_text(objective, result_data.get('target_volatility'), result_data.get('target_return'))}"
            f" ({objective})")
    if model_type == 'Markowitz':
        estimator = ('Historical mean' if result_data.get('returns_estimator') == 'historical'
                     else 'CAPM against SPY')
    else:
        estimator = 'market-implied prior' + (' blended with your views' if result_data.get('viewdict') else '')
    rows = [
        ('Model:', model_type),
        ('Goal:', goal),
        ('Expected returns:', estimator),
        ('Covariance:', 'Ledoit-Wolf shrinkage'),
    ]
    if result_data.get('l2_gamma') is not None:
        rows.append(('L2 regularization (gamma):', f"{result_data['l2_gamma']:.1f}"))
    rows.append(('Risk-free rate:', risk_free_text(result_data)))
    timestamp = result_data.get('timestamp', 'N/A')
    rows.append(('Run on:', timestamp[:10] if timestamp != 'N/A' else 'N/A'))
    for label, value in rows:
        pdf.cell(58, 6, label, new_x=XPos.RIGHT)
        # multi_cell: a goal with its target and textbook name can be long
        pdf.multi_cell(0, 6, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(5)
