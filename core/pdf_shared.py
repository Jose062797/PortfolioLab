"""
Shared PDF utilities for the portfolio reports (both models).

This module contains reusable chart generation and PDF section builders
used by the web PDF generator (utils/pdf_generator.py).

All chart functions return PNG image bytes (in-memory via BytesIO).
All PDF section functions accept an FPDF instance and modify it in place.
"""

import io
import logging
from datetime import datetime

from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from fpdf.enums import XPos, YPos

logger = logging.getLogger(__name__)

# Import constants — supports both `python core/pdf_shared.py` and `from core.pdf_shared import ...`
try:
    from constants import (
        ASSET_COLORS, MIN_WEIGHT_THRESHOLD, OBJECTIVE_LABELS, RETURN_COMPARISON_TOLERANCE,
        SHARPE_COMPARISON_TOLERANCE
    )
except ImportError:
    from core.constants import (
        ASSET_COLORS, MIN_WEIGHT_THRESHOLD, OBJECTIVE_LABELS, RETURN_COMPARISON_TOLERANCE,
        SHARPE_COMPARISON_TOLERANCE
    )

# Series colors of the web charts (utils/visualizations.py)
_PRIOR_COLOR, _VIEWS_COLOR, _POSTERIOR_COLOR = "#2E6FC7", "#F59E0B", "#10B981"
_PORTFOLIO_COLOR, _BENCHMARK_COLOR = "#2E6FC7", "#64748B"


# ═══════════════════════════════════════════════════════════════════
#  Chart Generation Functions  (all return bytes)
# ═══════════════════════════════════════════════════════════════════

def create_comparison_chart(
    market_prior: pd.Series,
    posterior: pd.Series,
    views: dict
) -> bytes:
    """Create comparison bar chart (Prior vs Posterior vs Views)."""
    fig = Figure(figsize=(7, 4))
    ax = fig.subplots()
    fig.patch.set_facecolor('white')

    # Same series, order and colors as the web chart (create_returns_comparison).
    # Assets without a view stay NaN, so they get no view bar rather than 0%.
    if views and len(views) > 0:
        # Extract view values — handle both dict and float formats
        view_series = pd.Series({
            k: (v.get('expected_return', v.get('expected', v))
                if isinstance(v, dict) else v)
            for k, v in views.items()
        })

        comparison_df = pd.DataFrame({
            'Market Prior': market_prior,
            'Your Views': view_series,
            'Posterior (BL)': posterior,
        }).reindex(market_prior.index) * 100
        comparison_df.plot.bar(ax=ax, width=0.8,
                               color=[_PRIOR_COLOR, _VIEWS_COLOR, _POSTERIOR_COLOR])
        ax.set_title('Market Prior, Your Views and Posterior', fontweight='bold', fontsize=12)
    else:
        comparison_df = pd.DataFrame({
            'Market Prior': market_prior,
            'Posterior (BL)': posterior,
        }) * 100
        comparison_df.plot.bar(ax=ax, width=0.8, color=[_PRIOR_COLOR, _POSTERIOR_COLOR])
        ax.set_title('Market Prior and Posterior', fontweight='bold', fontsize=12)

    ax.set_ylabel('Expected Annual Return (%)', fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(axis='y', alpha=0.3)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')

    fig.tight_layout()
    return _fig_to_bytes(fig)


MAX_PIE_SLICES = 6  # as the web (utils/visualizations.MAX_DONUT_SLICES)


def create_allocation_chart(weights: dict) -> bytes:
    """Portfolio allocation: a pie up to MAX_PIE_SLICES assets, horizontal
    bars (largest on top) beyond, like the web page's Allocation tab."""
    weights_series = pd.Series({
        k: v for k, v in weights.items()
        if v > MIN_WEIGHT_THRESHOLD
    })

    if len(weights_series) > MAX_PIE_SLICES:
        shown = weights_series.sort_values()
        fig = Figure(figsize=(7, max(3.5, 0.4 * len(shown) + 1)))
        ax = fig.subplots()
        fig.patch.set_facecolor('white')
        ax.barh(shown.index, shown.values * 100, color=ASSET_COLORS[0])
        for i, value in enumerate(shown.values * 100):
            ax.text(value, i, f' {value:.1f}%', va='center', fontsize=9)
        ax.set_xlim(0, shown.max() * 100 * 1.15)
        ax.set_xlabel('Weight (%)')
        ax.spines[['top', 'right']].set_visible(False)
        ax.set_title('Portfolio Allocation', fontweight='bold', fontsize=12)
        fig.tight_layout()
        return _fig_to_bytes(fig)

    fig = Figure(figsize=(6, 6))
    ax = fig.subplots()
    fig.patch.set_facecolor('white')
    # Colors handed out in the same order as the web pie (create_allocation_pie)
    colors = ASSET_COLORS[:len(weights_series)]
    # Percentages only on slices big enough to hold one; the table below lists every weight
    weights_series.plot.pie(ax=ax, autopct=lambda pct: f'{pct:.1f}%' if pct >= 3 else '',
                            colors=colors, startangle=90,
                            wedgeprops=dict(edgecolor='white', linewidth=1.5))
    ax.set_title('Portfolio Allocation', fontweight='bold', fontsize=12)
    ax.set_ylabel('')

    fig.tight_layout()
    return _fig_to_bytes(fig)


def create_correlation_heatmap(covariance, tickers: list) -> bytes | None:
    """
    Create correlation heatmap from covariance matrix. Returns None on error.

    `tickers` must be in the matrix's own row order (the result's
    'covariance_tickers'). Colors match the web heatmap: red for -1, blue
    for +1.
    """
    try:
        import seaborn as sns

        cov_df = pd.DataFrame(covariance, index=tickers, columns=tickers)
        std_devs = np.sqrt(np.diag(cov_df.values))
        correlation = cov_df / np.outer(std_devs, std_devs)

        fig = Figure(figsize=(8, 6))
        ax = fig.subplots()
        fig.patch.set_facecolor('white')

        sns.heatmap(
            correlation, annot=True, fmt='.2f', cmap='RdBu',
            center=0, vmin=-1, vmax=1, square=True, ax=ax,
            cbar_kws={'label': 'Correlation'}
        )
        ax.set_title('Asset Correlation Matrix', fontweight='bold', fontsize=12, pad=15)

        fig.tight_layout()
        return _fig_to_bytes(fig)
    except Exception:
        logger.exception("Error creating correlation heatmap")
        return None


def create_historical_chart(historical_data: dict,
                            model_type: str = 'Black-Litterman') -> bytes | None:
    """Create historical performance chart from backtest data (web colors and labels)."""
    try:
        fig = Figure(figsize=(10, 5))
        ax = fig.subplots()
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

        ax.plot(dates_dt, portfolio_pct, label=f'{model_type} Portfolio',
                color=_PORTFOLIO_COLOR, linewidth=2.5)
        ax.plot(dates_dt, spy_pct, label='SPY Benchmark',
                color=_BENCHMARK_COLOR, linewidth=2, linestyle='--')

        # Add final value annotations with offset to avoid overlap
        final_portfolio = portfolio_pct[-1]
        final_spy = spy_pct[-1]

        if final_portfolio > final_spy:
            ax.annotate(f'{final_portfolio:.1f}%', xy=(dates_dt[-1], final_portfolio),
                        xytext=(5, 8), textcoords='offset points',
                        fontsize=8, va='bottom', ha='left', color=_PORTFOLIO_COLOR, fontweight='bold')
            ax.annotate(f'{final_spy:.1f}%', xy=(dates_dt[-1], final_spy),
                        xytext=(5, -8), textcoords='offset points',
                        fontsize=8, va='top', ha='left', color=_BENCHMARK_COLOR, fontweight='bold')
        else:
            ax.annotate(f'{final_spy:.1f}%', xy=(dates_dt[-1], final_spy),
                        xytext=(5, 8), textcoords='offset points',
                        fontsize=8, va='bottom', ha='left', color=_BENCHMARK_COLOR, fontweight='bold')
            ax.annotate(f'{final_portfolio:.1f}%', xy=(dates_dt[-1], final_portfolio),
                        xytext=(5, -8), textcoords='offset points',
                        fontsize=8, va='top', ha='left', color=_PORTFOLIO_COLOR, fontweight='bold')

        ax.set_title('Historical Performance vs SPY Benchmark', fontweight='bold', fontsize=12)
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Cumulative Return (%)', fontsize=10)
        ax.legend(fontsize=9, loc='upper left')
        ax.grid(alpha=0.3)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.0f}%'))

        fig.tight_layout()
        return _fig_to_bytes(fig)
    except Exception:
        logger.exception("Error creating historical chart")
        return None


# ═══════════════════════════════════════════════════════════════════
#  PDF Section Builders  (modify FPDF instance in place)
# ═══════════════════════════════════════════════════════════════════

OBJECTIVE_DESCRIPTIONS = {
    'Min Variance': 'minimizes expected volatility',
    'Max Sharpe': 'maximizes the expected Sharpe ratio (3% risk-free rate)',
    'Maximise Return for a Given Risk': 'maximizes expected return with volatility of at most {target_volatility}%',
    'Minimise Risk for a Given Return': 'minimizes volatility for an expected return of at least {target_return}%',
}


def describe_objective(obj_function: str, target_volatility=None, target_return=None) -> str:
    """What the Markowitz objective does, with its target when it has one.

    Targets print as typed (12.5%), like goal_text: `:.0%` rounded them to
    whole percents, so the same PDF said 12% here and 12.5% in its breakdown
    (audit F1-01).
    """
    template = OBJECTIVE_DESCRIPTIONS.get(obj_function, 'optimizes the portfolio')
    return template.format(target_volatility=f"{(target_volatility or 0.0) * 100:g}",
                           target_return=f"{(target_return or 0.0) * 100:g}")


def add_methodology(pdf, result: dict) -> None:
    """Add the methodology section: what this run did, model by model."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Methodology', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.set_font('helvetica', '', 9)
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    gamma = result.get('l2_gamma')
    gamma_text = f"gamma = {gamma:.1f}" if gamma is not None else "see the settings"

    if result.get('model_type') == 'Markowitz':
        estimator = (
            "historical mean: each asset's compounded average annual return"
            if result.get('returns_estimator') == 'historical' else
            "CAPM: each asset's beta against SPY applied to the market's return "
            "above the risk-free rate"
        )
        objective = result.get('obj_function', 'Min Variance')
        methodology_text = (
            "Mean-variance optimization (Markowitz), following the PyPortfolioOpt cookbook:\n\n"
            f"- Expected returns: {estimator}, estimated from daily prices\n"
            "- Risk model: Ledoit-Wolf shrunk covariance matrix of daily returns\n"
            f"- Goal: {OBJECTIVE_LABELS.get(objective, objective)} ({objective}), which "
            f"{describe_objective(objective, result.get('target_volatility'), result.get('target_return'))}\n"
            f"- L2 regularization: {gamma_text}"
            + (" (none)" if not gamma else " (spreads the weights across assets)") + "\n"
            "- Risk-free rate: 3% a year"
        )
    else:
        n_views = len(result.get('viewdict') or {})
        views_text = (
            f"your views on {n_views} asset{'s' if n_views != 1 else ''}; each view's range is "
            "read as one standard deviation on either side, so a narrower range moves the "
            "posterior more"
            if n_views else
            "none, so the posterior equals the prior (market equilibrium)"
        )
        methodology_text = (
            "Black-Litterman model, following the PyPortfolioOpt cookbook:\n\n"
            "- Prior: the returns implied by market capitalizations (market equilibrium), with "
            "risk aversion estimated from SPY\n"
            f"- Views: {views_text}\n"
            "- Posterior: the Bayesian blend of prior and views, with a Ledoit-Wolf shrunk "
            "covariance matrix of daily returns\n"
            "- Optimization: highest expected Sharpe ratio on the posterior returns (3% "
            "risk-free rate), "
            # With gamma 0 the engine skips L2 entirely (audit F1-07)
            + (f"with an L2 penalty ({gamma_text}) that spreads the weights" if gamma
               else "with no L2 penalty (gamma = 0)")
        )
    pdf.multi_cell(available_width, 5, methodology_text)
    pdf.ln(5)


def add_disclaimers(pdf, model_type: str = 'Black-Litterman') -> None:
    """Add disclaimers page."""
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, 'Important Disclaimers', align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    available_width = pdf.w - pdf.l_margin - pdf.r_margin

    model_limitations = (
        "Mean-variance optimization depends on its estimates of expected return and "
        "risk, which are uncertain: small changes in the estimates can change the "
        "weights a lot."
        if model_type == 'Markowitz' else
        "The Black-Litterman model rests on assumptions about market equilibrium, "
        "investor views and how returns behave. Real markets can differ from them."
    )
    disclaimers = [
        ("Not Investment Advice",
         "This report is for informational and educational purposes only. It does not "
         "constitute investment advice, financial advice, trading advice, or any other "
         "sort of advice. You should not treat any of the report's content as such."),
        ("Consult Professionals",
         "Always do your own research and consult with a licensed financial advisor "
         "before making any investment decisions. Your financial situation is unique, "
         "and this analysis may not suit your circumstances."),
        ("Past Performance",
         "Past performance is not indicative of future results. Historical returns and "
         "the model's expected returns are shown for illustration only and may not "
         "reflect actual future performance."),
        ("Risk Disclosure",
         "All investments carry risk, including potential loss of principal. Prices "
         "can be volatile and unpredictable. The value of your investment may "
         "fluctuate over time."),
        ("Model Limitations", model_limitations),
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


def add_chart_description(pdf, chart_type: str, result: dict = None) -> None:
    """Add descriptive text after a chart (texts match the web page's captions)."""
    pdf.ln(2)
    pdf.set_font('helvetica', '', 9)
    result = result or {}

    objective = result.get('obj_function', 'Max Sharpe')
    descriptions = {
        'prior': (
            "The market-implied prior returns are the returns that make current "
            "market capitalizations the optimal portfolio, given the covariance matrix "
            "and a risk aversion estimated from SPY."
        ),
        'posterior': (
            "The posterior returns are the Black-Litterman model's blend of the "
            "market-implied returns and your views."
        ),
        'comparison': (
            "Prior: the returns implied by market capitalizations (the market "
            "equilibrium). Posterior: the Black-Litterman blend of the prior and your "
            "views, which the optimizer uses. Assets without a view have no view bar."
        ),
        'correlation': (
            "Correlations implied by the Ledoit-Wolf shrunk covariance matrix estimated "
            "from daily returns, the risk model both optimizers start from. Shrinkage "
            "pulls every correlation toward zero. Blue cells: assets that tend to move "
            "together; red cells: assets that tend to move in opposite directions."
        ),
        'allocation': (
            f"The weights are the optimizer's solution for the chosen goal "
            f"({OBJECTIVE_LABELS.get(objective, objective).lower()}). They follow from the "
            "model's estimates of return and risk, "
            "which are uncertain, and they are not a forecast. Shares are whole units "
            "bought at the last close with a price for every asset: Target Value is "
            "weight x budget, Actual Value is shares x price."
        ),
        'historical': (
            "Cumulative returns of the portfolio and of SPY over the backtest period. "
            "Past performance does not guarantee future results."
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
    period = historical_data.get('period', 'the backtest period')
    pdf.multi_cell(
        available_width, 5,
        f"In-sample backtest, {period}: the weights were estimated from this same price "
        "history, so it does not show how they would have done out of sample, and it "
        "tends to flatter the optimized portfolio. The target weights are kept every day "
        "(daily rebalancing); whole-share rounding, costs and taxes are ignored."
    )
    pdf.ln(2)


def add_historical_metrics(pdf, historical_data: dict,
                           model_type: str = 'Black-Litterman') -> None:
    """Add backtest metrics in card layout (matching web) and comparative analysis."""
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    gap = 4
    col_width = (available_width - gap) / 2
    card_height = 14

    portfolio_return   = float(historical_data["return"])
    portfolio_vol      = float(historical_data["volatility"])
    portfolio_sharpe   = float(historical_data["sharpe"])
    portfolio_md       = float(historical_data["max_drawdown"])
    portfolio_sortino  = float(historical_data["sortino"])
    portfolio_calmar   = float(historical_data["calmar"])

    spy_return  = float(historical_data["spy_return"])
    spy_vol     = float(historical_data["spy_volatility"])
    spy_sharpe  = float(historical_data["spy_sharpe"])
    spy_md      = float(historical_data["spy_max_drawdown"])
    spy_sortino = float(historical_data["spy_sortino"])
    spy_calmar  = float(historical_data["spy_calmar"])

    # Column titles (match web: <model> Portfolio | SPY Benchmark)
    pdf.ln(2)
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(col_width, 6, f'{model_type} Portfolio', align='C')
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
    # Row 4: Sharpe Ratio (realised from backtest returns; the web's word)
    _draw_metric_card(pdf, start_x, start_y, col_width, card_height,
                      'Sharpe Ratio', f'{portfolio_sharpe:.2f}')
    _draw_metric_card(pdf, start_x + col_width + gap, start_y, col_width, card_height,
                      'Sharpe Ratio', f'{spy_sharpe:.2f}')
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

    # Return comparison. These are annualized returns: "a year", or the text
    # read as total returns over the period (audit F1-17).
    if abs(return_diff) < RETURN_COMPARISON_TOLERANCE:
        analysis_parts.append(
            f"The portfolio returned {portfolio_return:.2f}% a year, roughly matching "
            f"the SPY benchmark ({spy_return:.2f}% a year)."
        )
    elif return_diff > 0:
        analysis_parts.append(
            f"The portfolio outperformed SPY by {return_diff:.2f} percentage "
            f"points a year ({portfolio_return:.2f}% vs {spy_return:.2f}%)."
        )
    else:
        analysis_parts.append(
            f"The portfolio underperformed SPY by {abs(return_diff):.2f} "
            f"percentage points a year ({portfolio_return:.2f}% vs {spy_return:.2f}%)."
        )

    # Volatility comparison
    if abs(vol_diff) < RETURN_COMPARISON_TOLERANCE:
        analysis_parts.append(
            f"Volatility was similar: {portfolio_vol:.2f}% for the portfolio, "
            f"{spy_vol:.2f}% for SPY."
        )
    elif vol_diff < 0:
        analysis_parts.append(
            f"Its volatility was lower ({portfolio_vol:.2f}% vs {spy_vol:.2f}%)."
        )
    else:
        analysis_parts.append(
            f"Its volatility was higher ({portfolio_vol:.2f}% vs {spy_vol:.2f}%)."
        )

    # Sharpe comparison
    if sharpe_diff > SHARPE_COMPARISON_TOLERANCE:
        analysis_parts.append(
            f"Its realized Sharpe ratio was higher ({portfolio_sharpe:.2f} vs {spy_sharpe:.2f})."
        )
    elif sharpe_diff < -SHARPE_COMPARISON_TOLERANCE:
        analysis_parts.append(
            f"Its realized Sharpe ratio was lower ({portfolio_sharpe:.2f} vs {spy_sharpe:.2f})."
        )
    else:
        analysis_parts.append(
            f"The realized Sharpe ratios were similar ({portfolio_sharpe:.2f} vs {spy_sharpe:.2f})."
        )
    analysis_parts.append(
        "These are in-sample results: the weights were chosen with this history in view."
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
    return buf.read()
