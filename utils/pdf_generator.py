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
    add_chart_to_pdf,
    add_historical_header,
    add_historical_metrics,
)
from core.constants import MIN_WEIGHT_THRESHOLD

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

    # Latest prices per ticker — extracted from prices_clean (last date row)
    latest_prices = {}
    prices_clean_dict = result_data.get('prices_clean', {})
    if prices_clean_dict:
        last_date = sorted(prices_clean_dict.keys())[-1]
        latest_prices = prices_clean_dict[last_date]  # {ticker: price}

    # Date ranges
    date_range = result_data.get('date_range', None)
    if date_range and len(date_range) == 2:
        data_start, data_end = date_range
    else:
        data_start = result_data.get('data_start_date', 'N/A')
        data_end = result_data.get('data_end_date', 'N/A')

    full_data_range = result_data.get('full_data_range', None)
    if full_data_range and len(full_data_range) == 2:
        full_start, full_end = full_data_range
    else:
        full_start, full_end = data_start, data_end

    num_assets = sum(1 for w in weights.values() if w > MIN_WEIGHT_THRESHOLD)

    # ── PAGE 1: Cover + Executive Summary + Metric Cards + Methodology ──
    _add_cover_page(pdf, portfolio_value, data_start, data_end,
                    logo_path, full_start, full_end, model_type, obj_function)
    _add_executive_summary(pdf, portfolio_value, num_assets, model_type, obj_function)
    _add_metric_cards(pdf, expected_return, volatility, sharpe_ratio,
                      portfolio_value, num_assets)
    add_methodology(pdf)

    # ── PAGE 2: Allocation (Tab 1) — chart first, then table ──
    pdf.add_page()
    _add_allocation_title(pdf)
    add_chart_to_pdf(pdf, create_allocation_chart(weights), width_scale=0.75)
    add_chart_description(pdf, 'allocation')
    _add_allocation_table(pdf, weights, allocation, portfolio_value, latest_prices)

    # ── PAGE 3: Returns Analysis (Tab 2) — only for Black-Litterman ──
    if model_type != "Markowitz" and len(market_prior) > 0:
        views_detail = result_data.get('views_detail', {})
        pdf.add_page()
        _add_returns_analysis(pdf, market_prior, posterior, views, views_detail)

    # ── PAGE 4: Historical Performance (Tab 3) ──
    if historical_data:
        pdf.add_page()
        logger.info("Historical data available, adding performance section")
        add_historical_header(pdf, historical_data)
        hist_chart = create_historical_chart(historical_data)
        if hist_chart:
            add_chart_to_pdf(pdf, hist_chart)
            add_chart_description(pdf, 'historical')
        else:
            logger.warning("Historical chart generation returned None")
        add_historical_metrics(pdf, historical_data)

    # ── PAGE 5: Correlation (Tab 4) ──
    if covariance is not None:
        corr_chart = create_correlation_heatmap(covariance, tickers)
        if corr_chart:
            pdf.add_page()
            pdf.set_font('helvetica', 'B', 14)
            pdf.cell(0, 8, 'Correlation Analysis',
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)
            add_chart_to_pdf(pdf, corr_chart)
            add_chart_description(pdf, 'correlation')

    # ── PAGE 6: Detailed Breakdown (Tab 5) ──
    pdf.add_page()
    _add_detailed_breakdown(pdf, weights, portfolio_value,
                            leftover, num_assets, data_start, data_end,
                            full_start, full_end, result_data)

    # ── PAGE 7: Disclaimers ──
    pdf.add_page()
    add_disclaimers(pdf)

    # Return PDF as bytes
    pdf_output = pdf.output()
    if isinstance(pdf_output, bytearray):
        return bytes(pdf_output)
    return pdf_output


# ═══════════════════════════════════════════════════════════════════
#  PDF Sections
# ═══════════════════════════════════════════════════════════════════

def _add_cover_page(pdf, portfolio_value, data_start, data_end,
                    logo_path, full_start=None, full_end=None,
                    model_type='Black-Litterman', obj_function='Max Sharpe'):
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
    # Show objective for Markowitz
    if model_type == 'Markowitz':
        pdf.set_font('helvetica', '', 16)
        pdf.cell(0, 10, f'Objective: {obj_function}', align='C',
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('helvetica', 'B', 24)
    pdf.cell(0, 12, 'Portfolio Report', align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(15)

    pdf.set_font('helvetica', '', 11)
    pdf.cell(0, 6, f'Portfolio Value: ${portfolio_value:,.0f}',
             align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
             align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if full_start and full_end and full_start != data_start:
        pdf.cell(0, 6,
                 f'Price Data: {full_start} to {full_end} (covariance estimation)',
                 align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6,
                 f'Common Period: {data_start} to {data_end} (backtest & allocation)',
                 align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    elif data_start != 'N/A' and data_end != 'N/A':
        pdf.cell(0, 6, f'Analysis Period: {data_start} to {data_end}',
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

    labels = ['Expected Return', 'Volatility', 'Sharpe (Ex-Ante)',
              'Portfolio Value', 'Assets']
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

    # Footnote: clarify ex-ante vs ex-post Sharpe for readers
    pdf.set_font('helvetica', 'I', 7)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 4,
             'Sharpe (Ex-Ante): model estimate from expected returns. '
             'Sharpe (Ex-Post): realised ratio from historical backtest (see Historical Performance).',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)


def _add_executive_summary(pdf, portfolio_value, n_assets,
                           model_type='Black-Litterman', obj_function='Max Sharpe'):
    """Add executive summary paragraph."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Executive Summary',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.set_font('helvetica', '', 10)
    available_width = pdf.w - pdf.l_margin - pdf.r_margin

    obj_descriptions = {
        'Max Sharpe': 'maximizes risk-adjusted returns (Sharpe ratio)',
        'Maximise Return for a Given Risk': 'maximizes return for a specified level of risk',
        'Min Variance': 'minimizes portfolio variance',
        'Minimise Risk for a Given Return': 'minimizes risk for a specified target return',
    }

    if model_type == "Markowitz":
        obj_desc = obj_descriptions.get(obj_function, 'optimizes the portfolio')
        summary_text = (
            f"This report presents an optimized portfolio allocation for "
            f"${portfolio_value:,.0f} across {n_assets} assets using "
            f"Mean-Variance Optimization (Markowitz) with the "
            f"{obj_function} objective, which {obj_desc}."
        )
    else:
        summary_text = (
            f"This report presents an optimized portfolio allocation for "
            f"${portfolio_value:,.0f} across {n_assets} assets using the "
            f"Black-Litterman model. The model combines market equilibrium "
            f"returns with investor views through a Bayesian framework, "
            f"producing a portfolio that maximizes risk-adjusted returns."
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
    """Add intro text and allocation table: Asset | Weight | Shares | Price | Actual Value.

    Mirrors the web UI's allocation table (visualizations.create_allocation_table).
    'Actual Value' = shares × latest price, matching exactly what the user would pay.
    Falls back to weight × portfolio_value when prices are unavailable.
    """
    pdf.set_font('helvetica', '', 9)
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.multi_cell(available_width, 5,
                   "Optimal portfolio weights and discrete share allocation:")
    pdf.ln(2)

    prices = latest_prices or {}
    has_prices = bool(prices)

    if has_prices:
        col_widths = [22, 25, 18, 28, 38]  # Asset | Weight | Shares | Price | Actual Value
        pdf.set_font('helvetica', 'B', 9)
        pdf.cell(col_widths[0], 6, 'Asset',        border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[1], 6, 'Weight',        border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[2], 6, 'Shares',        border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[3], 6, 'Price ($)',     border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[4], 6, 'Actual Value',  border=1, align='C',
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        col_widths = [25, 28, 22, 38]  # Asset | Weight | Shares | Target Value
        pdf.set_font('helvetica', 'B', 9)
        pdf.cell(col_widths[0], 6, 'Asset',         border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[1], 6, 'Weight',         border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[2], 6, 'Shares',         border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[3], 6, 'Target Value',   border=1, align='C',
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('helvetica', '', 8)
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)

    for ticker, weight in sorted_weights:
        if weight > MIN_WEIGHT_THRESHOLD:
            shares = allocation.get(ticker, 0)
            pdf.cell(col_widths[0], 6, ticker,           border=1, align='C', new_x=XPos.RIGHT)
            pdf.cell(col_widths[1], 6, f'{weight*100:.2f}%', border=1, align='C', new_x=XPos.RIGHT)
            pdf.cell(col_widths[2], 6, str(shares),      border=1, align='C', new_x=XPos.RIGHT)
            if has_prices:
                price = prices.get(ticker)
                actual_value = shares * price if (price and shares > 0) else None
                price_str  = f'${price:,.2f}'        if price        else 'N/A'
                value_str  = f'${actual_value:,.2f}' if actual_value else 'N/A'
                pdf.cell(col_widths[3], 6, price_str, border=1, align='C', new_x=XPos.RIGHT)
                pdf.cell(col_widths[4], 6, value_str, border=1, align='C',
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            else:
                target_value = weight * portfolio_value
                pdf.cell(col_widths[3], 6, f'${target_value:,.2f}', border=1, align='C',
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)

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
        pdf.cell(col_widths[3], 5, 'Lower', border=1, align='C', new_x=XPos.RIGHT)
        pdf.cell(col_widths[4], 5, 'Upper', border=1, align='C', new_x=XPos.RIGHT)
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

def _add_detailed_breakdown(pdf, weights, portfolio_value,
                            leftover, num_assets, data_start, data_end,
                            full_start, full_end, result_data):
    """Add detailed breakdown: Portfolio Summary (matching web Tab 5)."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Detailed Breakdown',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # ── Portfolio Summary ──
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 7, 'Portfolio Summary',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.set_font('helvetica', '', 10)
    pdf.cell(50, 6, 'Total Value:', new_x=XPos.RIGHT)
    pdf.cell(0, 6, f'${portfolio_value:,.2f}',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.cell(50, 6, 'Number of Assets:', new_x=XPos.RIGHT)
    pdf.cell(0, 6, str(num_assets),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.cell(50, 6, 'Cash Remaining:', new_x=XPos.RIGHT)
    pdf.cell(0, 6, f'${leftover:.2f}',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if full_start and full_end and full_start != data_start:
        pdf.cell(50, 6, 'Price Data:', new_x=XPos.RIGHT)
        pdf.cell(0, 6, f'{full_start} to {full_end} (covariance)',
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(50, 6, 'Common Period:', new_x=XPos.RIGHT)
        pdf.cell(0, 6, f'{data_start} to {data_end} (backtest)',
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    elif data_start != 'N/A' and data_end != 'N/A':
        pdf.cell(50, 6, 'Analysis Period:', new_x=XPos.RIGHT)
        pdf.cell(0, 6, f'{data_start} to {data_end}',
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    timestamp = result_data.get('timestamp', 'N/A')
    pdf.cell(50, 6, 'Optimization Date:', new_x=XPos.RIGHT)
    pdf.cell(0, 6, timestamp[:10] if timestamp != 'N/A' else 'N/A',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(5)
