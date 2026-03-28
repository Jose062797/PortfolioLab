"""
Shared PDF utilities for Black-Litterman Portfolio Reports.

This module contains reusable chart generation and PDF section builders
used by both the CLI report generator (core/report.py) and the web PDF
generator (utils/pdf_generator.py).

All chart functions return PNG image bytes (in-memory via BytesIO).
All PDF section functions accept an FPDF instance and modify it in place.
"""

import io
import logging
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from fpdf.enums import XPos, YPos

logger = logging.getLogger(__name__)

# Import constants — supports both `python core/pdf_shared.py` and `from core.pdf_shared import ...`
try:
    from constants import (
        MIN_WEIGHT_THRESHOLD, RETURN_COMPARISON_TOLERANCE,
        SHARPE_COMPARISON_TOLERANCE
    )
except ImportError:
    from core.constants import (
        MIN_WEIGHT_THRESHOLD, RETURN_COMPARISON_TOLERANCE,
        SHARPE_COMPARISON_TOLERANCE
    )


# ═══════════════════════════════════════════════════════════════════
#  Chart Generation Functions  (all return bytes)
# ═══════════════════════════════════════════════════════════════════

def create_prior_chart(market_prior: pd.Series) -> bytes:
    """Create market prior returns horizontal bar chart."""
    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor('white')

    sorted_prior = market_prior.sort_values(ascending=True)
    colors = ['green' if x > 0 else 'red' for x in sorted_prior.values]
    sorted_prior.plot.barh(ax=ax, color=colors, alpha=0.7)
    ax.set_title('Market-Implied Prior Returns', fontweight='bold', fontsize=12)
    ax.set_xlabel('Expected Annual Return', fontsize=10)
    ax.grid(axis='x', alpha=0.3)
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)

    plt.tight_layout()
    return _fig_to_bytes(fig)


def create_posterior_chart(posterior: pd.Series) -> bytes:
    """Create posterior returns horizontal bar chart."""
    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor('white')

    sorted_post = posterior.sort_values(ascending=True)
    colors = ['green' if x > 0 else 'red' for x in sorted_post.values]
    sorted_post.plot.barh(ax=ax, color=colors, alpha=0.7)
    ax.set_title('Black-Litterman Posterior Returns', fontweight='bold', fontsize=12)
    ax.set_xlabel('Expected Annual Return', fontsize=10)
    ax.grid(axis='x', alpha=0.3)
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)

    plt.tight_layout()
    return _fig_to_bytes(fig)


def create_comparison_chart(
    market_prior: pd.Series,
    posterior: pd.Series,
    views: dict
) -> bytes:
    """Create comparison bar chart (Prior vs Posterior vs Views)."""
    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor('white')

    if views and len(views) > 0:
        # Extract view values — handle both dict and float formats
        view_series = pd.Series({
            k: (v.get('expected_return', v.get('expected', v))
                if isinstance(v, dict) else v)
            for k, v in views.items()
        })

        comparison_df = pd.DataFrame({
            'Prior': market_prior,
            'Posterior': posterior,
            'Views': view_series
        }).fillna(0)
        comparison_df.plot.bar(ax=ax, width=0.8)
        ax.set_title('Prior vs Posterior vs Views', fontweight='bold', fontsize=12)
    else:
        comparison_df = pd.DataFrame({
            'Prior': market_prior,
            'Posterior': posterior
        })
        comparison_df.plot.bar(ax=ax, width=0.8)
        ax.set_title('Prior vs Posterior', fontweight='bold', fontsize=12)

    ax.set_ylabel('Expected Return', fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(axis='y', alpha=0.3)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    return _fig_to_bytes(fig)


def create_allocation_chart(weights: dict) -> bytes:
    """Create portfolio allocation pie chart."""
    fig, ax = plt.subplots(figsize=(6, 6))
    fig.patch.set_facecolor('white')

    weights_series = pd.Series({
        k: v for k, v in weights.items()
        if v > MIN_WEIGHT_THRESHOLD
    })
    colors = plt.cm.Set3(range(len(weights_series)))
    weights_series.plot.pie(ax=ax, autopct='%1.1f%%', colors=colors, startangle=90)
    ax.set_title('Portfolio Allocation', fontweight='bold', fontsize=12)
    ax.set_ylabel('')

    plt.tight_layout()
    return _fig_to_bytes(fig)


def create_correlation_heatmap(covariance, tickers: list) -> bytes | None:
    """Create correlation heatmap from covariance matrix. Returns None on error."""
    try:
        import seaborn as sns

        cov_df = pd.DataFrame(covariance, index=tickers, columns=tickers)
        std_devs = np.sqrt(np.diag(cov_df.values))
        correlation = cov_df / np.outer(std_devs, std_devs)

        fig, ax = plt.subplots(figsize=(8, 6))
        fig.patch.set_facecolor('white')

        sns.heatmap(
            correlation, annot=True, fmt='.2f', cmap='RdYlGn_r',
            center=0, vmin=-1, vmax=1, square=True, ax=ax,
            cbar_kws={'label': 'Correlation'}
        )
        ax.set_title('Asset Correlation Matrix', fontweight='bold', fontsize=12, pad=15)

        plt.tight_layout()
        return _fig_to_bytes(fig)
    except Exception as e:
        logger.error("Error creating correlation heatmap: %s", e)
        return None


def create_historical_chart(historical_data: dict) -> bytes | None:
    """Create historical performance chart from backtest data."""
    try:
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor('white')

        # Use percentage returns (consistent with web)
        portfolio_pct = historical_data.get('portfolio_pct')
        spy_pct = historical_data.get('spy_pct')
        dates = historical_data.get('dates')

        # Fallback: calculate from dollar values if percentage data not available
        if portfolio_pct is None or spy_pct is None:
            portfolio_values = historical_data.get('portfolio_values')
            spy_values = historical_data.get('spy_values')

            if portfolio_values is not None and spy_values is not None:
                portfolio_pct = [(v / portfolio_values[0] - 1) * 100 for v in portfolio_values]
                spy_pct = [(v / spy_values[0] - 1) * 100 for v in spy_values]

        if portfolio_pct is None or spy_pct is None or dates is None:
            return None

        # Convert dates to datetime if they are strings
        if dates and isinstance(dates[0], str):
            dates_dt = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
        else:
            dates_dt = list(dates)

        ax.plot(dates_dt, portfolio_pct, label='BL Portfolio',
                color='#1f77b4', linewidth=2.5)
        ax.plot(dates_dt, spy_pct, label='SPY Benchmark',
                color='#d62728', linewidth=2, alpha=0.7, linestyle='--')

        # Add final value annotations with offset to avoid overlap
        final_bl = portfolio_pct[-1] if not isinstance(portfolio_pct[-1], (list,)) else portfolio_pct[-1]
        final_spy = spy_pct[-1] if not isinstance(spy_pct[-1], (list,)) else spy_pct[-1]

        if final_bl > final_spy:
            ax.annotate(f'{final_bl:.1f}%', xy=(dates_dt[-1], final_bl),
                        xytext=(5, 8), textcoords='offset points',
                        fontsize=8, va='bottom', ha='left', color='#1f77b4', fontweight='bold')
            ax.annotate(f'{final_spy:.1f}%', xy=(dates_dt[-1], final_spy),
                        xytext=(5, -8), textcoords='offset points',
                        fontsize=8, va='top', ha='left', color='#d62728', fontweight='bold')
        else:
            ax.annotate(f'{final_spy:.1f}%', xy=(dates_dt[-1], final_spy),
                        xytext=(5, 8), textcoords='offset points',
                        fontsize=8, va='bottom', ha='left', color='#d62728', fontweight='bold')
            ax.annotate(f'{final_bl:.1f}%', xy=(dates_dt[-1], final_bl),
                        xytext=(5, -8), textcoords='offset points',
                        fontsize=8, va='top', ha='left', color='#1f77b4', fontweight='bold')

        ax.set_title('Historical Performance vs SPY Benchmark', fontweight='bold', fontsize=12)
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Cumulative Return (%)', fontsize=10)
        ax.legend(fontsize=9, loc='upper left')
        ax.grid(alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0f}%'))

        plt.tight_layout()
        return _fig_to_bytes(fig)
    except Exception as e:
        logger.error("Error creating historical chart: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════
#  PDF Section Builders  (modify FPDF instance in place)
# ═══════════════════════════════════════════════════════════════════

def add_methodology(pdf) -> None:
    """Add methodology explanation section."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Methodology', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.set_font('helvetica', '', 9)
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    methodology_text = (
        "The Black-Litterman model combines market equilibrium with your investment "
        "views to generate optimal portfolio allocations. Key features:\n\n"
        "- Market Equilibrium: Uses market capitalization and historical returns to "
        "establish baseline expected returns\n"
        "- Your Views: Incorporates your expectations about specific assets with "
        "appropriate confidence levels\n"
        "- Bayesian Framework: Blends market consensus with your insights in a "
        "statistically rigorous way\n"
        "- Risk Optimization: Maximizes Sharpe ratio while respecting your view "
        "uncertainties"
    )
    pdf.multi_cell(available_width, 5, methodology_text)
    pdf.ln(5)


def add_disclaimers(pdf) -> None:
    """Add disclaimers page."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, 'Important Disclaimers', align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    available_width = pdf.w - pdf.l_margin - pdf.r_margin

    disclaimers = [
        ("Not Investment Advice",
         "This report is for informational and educational purposes only. It does not "
         "constitute investment advice, financial advice, trading advice, or any other "
         "sort of advice. You should not treat any of the report's content as such."),
        ("Consult Professionals",
         "Always do your own research and consult with a licensed financial advisor "
         "before making any investment decisions. Your financial situation is unique, "
         "and any recommendations may not be suitable for your circumstances."),
        ("Past Performance",
         "Past performance is not indicative of future results. Historical returns, "
         "expected returns, and probability projections are provided for illustrative "
         "purposes only and may not reflect actual future performance."),
        ("Risk Disclosure",
         "All investments carry risk, including potential loss of principal. Stock "
         "prices can be volatile and unpredictable. The value of your investment may "
         "fluctuate over time."),
        ("Model Limitations",
         "The Black-Litterman model is a mathematical framework that makes certain "
         "assumptions about markets and returns. Real-world conditions may differ "
         "from model assumptions."),
        ("No Guarantees",
         "No representation is being made that any account will or is likely to "
         "achieve profits or losses similar to those shown. Diversification does not "
         "guarantee profits or protect against losses."),
        ("Transaction Costs",
         "This analysis does not account for transaction costs, taxes, fees, or "
         "other expenses that may apply to your specific situation."),
        ("Market Conditions",
         "Market conditions change constantly. This analysis is based on data "
         "available at the time of generation and may become outdated quickly."),
    ]

    pdf.set_font('helvetica', '', 8)
    for title, text in disclaimers:
        pdf.set_font('helvetica', 'B', 9)
        pdf.cell(available_width, 6, title,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('helvetica', '', 8)
        pdf.multi_cell(available_width, 4, text)
        pdf.ln(2)


def add_chart_description(pdf, chart_type: str) -> None:
    """Add descriptive text after a chart."""
    pdf.ln(2)
    pdf.set_font('helvetica', '', 9)

    descriptions = {
        'prior': (
            "The market-implied prior returns reflect current market expectations "
            "based on asset capitalizations and historical risk premiums."
        ),
        'posterior': (
            "The posterior returns represent the Black-Litterman model's optimal "
            "blend of market expectations and your personal views."
        ),
        'comparison': (
            "This comparison shows how the Black-Litterman framework reconciles "
            "market expectations (Prior) with your views to produce the final "
            "expected returns (Posterior)."
        ),
        'correlation': (
            "The correlation matrix shows how assets move together. Strong "
            "positive correlations (red) indicate assets that tend to move in the "
            "same direction, while negative correlations (blue) suggest "
            "diversification benefits."
        ),
        'allocation': (
            "The allocation reflects the optimizer's solution for maximizing "
            "risk-adjusted returns. Larger positions indicate assets with "
            "attractive return prospects relative to their risk."
        ),
        'historical': (
            "This historical backtest shows how the recommended portfolio would "
            "have performed over the analysis period compared to the SPY benchmark. "
            "Note that past performance does not guarantee future results."
        ),
    }

    text = descriptions.get(chart_type, "")
    if text:
        available_width = pdf.w - pdf.l_margin - pdf.r_margin
        pdf.multi_cell(available_width, 4, text)
        pdf.ln(3)


def add_chart_to_pdf(pdf, image_bytes: bytes, width_scale: float = 1.0) -> None:
    """Add chart image (as bytes) to PDF with auto page-break.

    width_scale: scale factor for display width (e.g. 0.75 for 75% size). Default 1.0.
    """
    if not image_bytes:
        return

    from PIL import Image

    img_io = io.BytesIO(image_bytes)
    img = Image.open(img_io)
    img_width, img_height = img.size
    aspect_ratio = img_height / img_width

    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    chart_width = min(available_width * 0.9, 180) * width_scale
    chart_height = chart_width * aspect_ratio

    # Check space
    space_needed = chart_height + 10
    space_available = pdf.h - pdf.get_y() - pdf.b_margin
    if space_available < space_needed:
        pdf.add_page()

    pdf.ln(3)
    x_position = pdf.l_margin + (available_width - chart_width) / 2

    # Pass BytesIO directly — fpdf2 supports file-like objects, no temp file needed
    img_io.seek(0)
    pdf.image(img_io, x=x_position, y=pdf.get_y(), w=chart_width)

    pdf.set_y(pdf.get_y() + chart_height + 3)


def add_historical_header(pdf, historical_data: dict) -> None:
    """Add Historical Performance title and introductory text (before chart)."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Historical Performance',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.set_font('helvetica', '', 9)
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    period = historical_data.get('period', '5 years')
    pdf.multi_cell(
        available_width, 5,
        f"Performance if this portfolio had been held during the period {period}:"
    )
    pdf.ln(2)


def add_historical_metrics(pdf, historical_data: dict) -> None:
    """Add backtest metrics in card layout (matching web) and comparative analysis."""
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    gap = 4
    col_width = (available_width - gap) / 2
    card_height = 14

    portfolio_return = float(historical_data.get("return") or 0)
    portfolio_vol = float(historical_data.get("volatility") or 0)
    portfolio_sharpe = float(historical_data.get("sharpe") or 0)
    portfolio_md = float(historical_data.get("max_drawdown") or 0)
    portfolio_sortino = float(historical_data.get("sortino") or 0)
    portfolio_calmar = float(historical_data.get("calmar") or 0)

    spy_return = float(historical_data.get("spy_return") or 0)
    spy_vol = float(historical_data.get("spy_volatility") or 0)
    spy_sharpe = float(historical_data.get("spy_sharpe") or 0)
    spy_md = float(historical_data.get("spy_max_drawdown") or 0)
    spy_sortino = float(historical_data.get("spy_sortino") or 0)
    spy_calmar = float(historical_data.get("spy_calmar") or 0)

    # Column titles (match web: BL Portfolio | SPY Benchmark)
    pdf.ln(2)
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(col_width, 6, 'BL Portfolio', align='C')
    pdf.cell(col_width, 6, 'SPY Benchmark', align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    start_x = pdf.l_margin
    start_y = pdf.get_y()

    # Check space for 6 rows of cards (about 6 * 16 = 96 units)
    if pdf.h - start_y - pdf.b_margin < 100:
        pdf.add_page()
        start_y = pdf.get_y()

    # Row 1: Annualized Return
    _draw_metric_card(pdf, start_x, start_y, col_width, card_height,
                      'Annualized Return', f'{portfolio_return:.2f}%')
    _draw_metric_card(pdf, start_x + col_width + gap, start_y, col_width, card_height,
                      'Annualized Return', f'{spy_return:.2f}%')
    start_y += card_height + 2
    # Row 2: Annualized Volatility
    _draw_metric_card(pdf, start_x, start_y, col_width, card_height,
                      'Annualized Volatility', f'{portfolio_vol:.2f}%')
    _draw_metric_card(pdf, start_x + col_width + gap, start_y, col_width, card_height,
                      'Annualized Volatility', f'{spy_vol:.2f}%')
    start_y += card_height + 2
    # Row 3: Max Drawdown
    _draw_metric_card(pdf, start_x, start_y, col_width, card_height,
                      'Max Drawdown', f'{portfolio_md:.2f}%')
    _draw_metric_card(pdf, start_x + col_width + gap, start_y, col_width, card_height,
                      'Max Drawdown', f'{spy_md:.2f}%')
    start_y += card_height + 2
    # Row 4: Sharpe Ratio (ex-post — realised from backtest returns)
    _draw_metric_card(pdf, start_x, start_y, col_width, card_height,
                      'Sharpe (Ex-Post)', f'{portfolio_sharpe:.2f}')
    _draw_metric_card(pdf, start_x + col_width + gap, start_y, col_width, card_height,
                      'Sharpe (Ex-Post)', f'{spy_sharpe:.2f}')
    start_y += card_height + 2
    # Row 5: Sortino Ratio
    _draw_metric_card(pdf, start_x, start_y, col_width, card_height,
                      'Sortino Ratio', f'{portfolio_sortino:.2f}')
    _draw_metric_card(pdf, start_x + col_width + gap, start_y, col_width, card_height,
                      'Sortino Ratio', f'{spy_sortino:.2f}')
    start_y += card_height + 2
    # Row 6: Calmar Ratio
    _draw_metric_card(pdf, start_x, start_y, col_width, card_height,
                      'Calmar Ratio', f'{portfolio_calmar:.2f}')
    _draw_metric_card(pdf, start_x + col_width + gap, start_y, col_width, card_height,
                      'Calmar Ratio', f'{spy_calmar:.2f}')

    pdf.set_y(start_y + card_height + 5)
    pdf.set_text_color(0, 0, 0)

    # Comparative Analysis
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'Comparative Analysis:',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('helvetica', '', 9)

    return_diff = portfolio_return - spy_return
    vol_diff = portfolio_vol - spy_vol
    sharpe_diff = portfolio_sharpe - spy_sharpe

    analysis_parts = []

    # Return comparison
    if abs(return_diff) < RETURN_COMPARISON_TOLERANCE:
        analysis_parts.append(
            f"The portfolio returned {portfolio_return:.2f}%, roughly matching "
            f"the SPY benchmark ({spy_return:.2f}%)."
        )
    elif return_diff > 0:
        analysis_parts.append(
            f"The portfolio outperformed SPY by {return_diff:.2f} percentage "
            f"points ({portfolio_return:.2f}% vs {spy_return:.2f}%)."
        )
    else:
        analysis_parts.append(
            f"The portfolio underperformed SPY by {abs(return_diff):.2f} "
            f"percentage points ({portfolio_return:.2f}% vs {spy_return:.2f}%)."
        )

    # Volatility comparison
    if abs(vol_diff) < RETURN_COMPARISON_TOLERANCE:
        analysis_parts.append(
            f"Risk levels were similar, with portfolio volatility at "
            f"{portfolio_vol:.2f}% compared to SPY's {spy_vol:.2f}%."
        )
    elif vol_diff < 0:
        analysis_parts.append(
            f"The portfolio exhibited lower volatility ({portfolio_vol:.2f}% "
            f"vs {spy_vol:.2f}%), suggesting better risk management."
        )
    else:
        analysis_parts.append(
            f"The portfolio showed higher volatility ({portfolio_vol:.2f}% "
            f"vs {spy_vol:.2f}%), reflecting a more aggressive risk profile."
        )

    # Sharpe comparison
    if sharpe_diff > SHARPE_COMPARISON_TOLERANCE:
        analysis_parts.append(
            f"The portfolio achieved a superior risk-adjusted return "
            f"(Sharpe: {portfolio_sharpe:.2f} vs {spy_sharpe:.2f})."
        )
    elif sharpe_diff < -SHARPE_COMPARISON_TOLERANCE:
        analysis_parts.append(
            f"The benchmark demonstrated better risk-adjusted performance "
            f"(Sharpe: {spy_sharpe:.2f} vs {portfolio_sharpe:.2f})."
        )
    else:
        analysis_parts.append(
            f"Risk-adjusted returns were comparable (Sharpe: "
            f"{portfolio_sharpe:.2f} vs {spy_sharpe:.2f})."
        )

    analysis_text = " ".join(analysis_parts)
    pdf.multi_cell(available_width, 4, analysis_text)
    pdf.ln(3)


# ═══════════════════════════════════════════════════════════════════
#  Internal Helpers
# ═══════════════════════════════════════════════════════════════════

# Web design tokens for metric cards (match utils/styles.py)
_LABEL_COLOR = (107, 114, 128)   # --color-text-secondary #6B7280
_VALUE_COLOR = (27, 58, 92)      # --color-primary #1B3A5C (dark blue, reads almost black)
_CARD_BORDER_COLOR = (200, 200, 200)


def _draw_metric_card(pdf, x: float, y: float, w: float, h: float,
                      label: str, value: str) -> None:
    """Draw a single metric card: bordered box, gray label on top, bold value below.
    Matches web st.metric style (label = uppercase-ish, value = color-primary)."""
    pdf.set_draw_color(*_CARD_BORDER_COLOR)
    pdf.rect(x, y, w, h)
    pdf.set_xy(x, y + 2)
    pdf.set_font('helvetica', '', 7)
    pdf.set_text_color(*_LABEL_COLOR)
    pdf.cell(w, 5, label, align='C')
    pdf.set_xy(x, y + 7)
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_text_color(*_VALUE_COLOR)
    pdf.cell(w, 7, value, align='C')
    pdf.set_text_color(0, 0, 0)


def _fig_to_bytes(fig) -> bytes:
    """Convert a matplotlib figure to PNG bytes and close it."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return buf.read()
