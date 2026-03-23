from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots


PALETTE = {
    "bg": "#0E1117",
    "card": "#151A23",
    "grid": "rgba(148,163,184,0.10)",
    "text": "#E5E7EB",
    "muted": "#94A3B8",
    "blue": "#3B82F6",
    "green": "#22C55E",
    "red": "#EF4444",
    "warning": "#F59E0B",
}


def _style(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#F8FAFC")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=12, r=12, t=44, b=12),
        font=dict(family="Inter, Segoe UI, sans-serif", color=PALETTE["text"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(color=PALETTE["muted"])),
        hoverlabel=dict(bgcolor=PALETTE["card"], font_size=12, font_family="Inter", font_color=PALETTE["text"]),
    )
    fig.update_xaxes(showgrid=False, showline=False, color=PALETTE["muted"])
    fig.update_yaxes(gridcolor=PALETTE["grid"], zeroline=False, color=PALETTE["muted"])
    return fig


def line_bar_chart(frame, metric: str, title: str, yaxis_tickformat: str | None = None) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(
        x=frame["period"],
        y=frame[f"{metric}_plan"],
        name="Projected",
        mode="lines",
        line=dict(color=PALETTE["blue"], width=3),
        hovertemplate="Month=%{x|%b %Y}<br>Projected=%{y:,.2f}<extra></extra>",
    )
    fig.add_scatter(
        x=frame["period"],
        y=frame[f"{metric}_actual"],
        name="Actual",
        mode="lines+markers",
        line=dict(color=PALETTE["green"], width=3),
        marker=dict(size=6),
        hovertemplate="Month=%{x|%b %Y}<br>Actual=%{y:,.2f}<extra></extra>",
    )
    if yaxis_tickformat:
        fig.update_yaxes(tickformat=yaxis_tickformat)
    return _style(fig, title)


def variance_combo(frame, metric: str, title: str) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(
        x=frame["period"],
        y=frame[f"{metric}_variance"],
        name="Variance Dollars",
        marker_color=PALETTE["warning"],
        hovertemplate="Month=%{x|%b %Y}<br>Variance=%{y:,.2f}<extra></extra>",
    )
    fig.add_scatter(
        x=frame["period"],
        y=frame[f"{metric}_variance_pct"],
        name="Variance %",
        mode="lines",
        line=dict(color=PALETTE["blue"], width=3),
        secondary_y=True,
        hovertemplate="Month=%{x|%b %Y}<br>Variance %%=%{y:.1%}<extra></extra>",
    )
    fig.update_yaxes(tickformat=".0%", secondary_y=True)
    return _style(fig, title)


def scenario_cash_chart(scenarios: dict[str, object], safety_threshold: float) -> go.Figure:
    fig = go.Figure()
    colors = {"Best Case": PALETTE["green"], "Medium Case": PALETTE["blue"], "Worst Case": PALETTE["red"], "Base Case": PALETTE["blue"]}
    fig.add_hrect(y0=-10000000, y1=safety_threshold, fillcolor="rgba(239,68,68,0.12)", line_width=0)
    fig.add_hline(y=safety_threshold, line_dash="dash", line_color=PALETTE["red"], annotation_text="Cash threshold", annotation_font_color=PALETTE["muted"])
    for name, frame in scenarios.items():
        fig.add_scatter(
            x=frame["period"],
            y=frame["cash_balance"],
            name=name,
            mode="lines",
            line=dict(width=3, color=colors.get(name, PALETTE["muted"])),
            hovertemplate="Month=%{x|%b %Y}<br>Cash=%{y:,.0f}<extra></extra>",
        )
    return _style(fig, "Cash Balance Projection")


def operating_metrics_chart(frame, metric: str, title: str, color: str) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(
        x=frame["period"],
        y=frame[metric],
        mode="lines+markers",
        line=dict(color=color, width=3),
        marker=dict(size=6),
        name=title,
        hovertemplate="Month=%{x|%b %Y}<br>Value=%{y:,.2f}<extra></extra>",
    )
    return _style(fig, title)


def multi_scenario_metric_chart(scenarios: dict[str, object], metric: str, title: str) -> go.Figure:
    fig = go.Figure()
    colors = {"Best Case": PALETTE["green"], "Medium Case": PALETTE["blue"], "Worst Case": PALETTE["red"], "Base Case": PALETTE["blue"]}
    for name, frame in scenarios.items():
        fig.add_scatter(
            x=frame["period"],
            y=frame[metric],
            name=name,
            mode="lines",
            line=dict(width=3, color=colors.get(name, PALETTE["muted"])),
            hovertemplate="Month=%{x|%b %Y}<br>Value=%{y:,.2f}<extra></extra>",
        )
    return _style(fig, title)


def margin_trend_chart(frame) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(
        x=frame["period"],
        y=frame["gross_margin_pct_plan"],
        name="Projected Margin",
        mode="lines",
        line=dict(color=PALETTE["blue"], width=3),
        hovertemplate="Month=%{x|%b %Y}<br>Projected=%{y:.1%}<extra></extra>",
    )
    fig.add_scatter(
        x=frame["period"],
        y=frame["gross_margin_pct_actual"],
        name="Actual Margin",
        mode="lines+markers",
        line=dict(color=PALETTE["green"], width=3),
        marker=dict(size=6),
        hovertemplate="Month=%{x|%b %Y}<br>Actual=%{y:.1%}<extra></extra>",
    )
    fig.update_yaxes(tickformat=".0%")
    return _style(fig, "Margin vs Plan")


def waterfall_chart(row) -> go.Figure:
    values = [
        row.get("revenue_actual", 0) or 0,
        -((row.get("revenue_actual", 0) or 0) - (row.get("gross_margin_pct_actual", 0) or 0) * (row.get("revenue_actual", 0) or 0)),
        -(row.get("payroll_actual", 0) or 0),
        -(row.get("operating_expenses_actual", 0) or 0),
        -(row.get("owner_draws_actual", 0) or 0),
        -(row.get("loan_payments_actual", 0) or 0),
        0,
    ]
    fig = go.Figure(
        go.Waterfall(
            measure=["relative", "relative", "relative", "relative", "relative", "relative", "total"],
            x=["Revenue", "COGS", "Payroll", "OpEx", "Owner Draws", "Loan Payments", "Cash Flow"],
            y=values,
            connector={"line": {"color": PALETTE["muted"]}},
            increasing={"marker": {"color": PALETTE["green"]}},
            decreasing={"marker": {"color": PALETTE["red"]}},
            totals={"marker": {"color": PALETTE["blue"]}},
            hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>",
        )
    )
    return _style(fig, "Revenue to Cash Flow")
