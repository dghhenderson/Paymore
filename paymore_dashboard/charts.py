from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots


PALETTE = {
    "bg": "#0A0C11",
    "card": "#161A23",
    "grid": "rgba(148,163,184,0.08)",
    "axis": "rgba(148,163,184,0.18)",
    "text": "#E6E8EE",
    "heading": "#F8FAFC",
    "muted": "#8B93A7",
    "blue": "#818CF8",
    "green": "#34D399",
    "red": "#F87171",
    "warning": "#FBBF24",
}

SCENARIO_COLORS = {
    "Best Case": PALETTE["green"],
    "Medium Case": PALETTE["blue"],
    "Base Case": PALETTE["blue"],
    "Worst Case": PALETTE["red"],
}


def _fill(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _style(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", y=0.97, font=dict(size=15, color=PALETTE["heading"], weight=600)),
        height=330,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=64, b=8),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", size=12, color=PALETTE["muted"]),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1,
            font=dict(color=PALETTE["muted"], size=12), bgcolor="rgba(0,0,0,0)", itemclick="toggleothers",
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=PALETTE["card"], bordercolor=PALETTE["axis"], font_size=12, font_family="Inter", font_color=PALETTE["text"]),
        bargap=0.35,
    )
    fig.update_xaxes(
        showgrid=False, showline=True, linecolor=PALETTE["axis"], ticks="", color=PALETTE["muted"], automargin=True,
        showspikes=True, spikemode="across", spikethickness=1, spikedash="dot", spikecolor=PALETTE["axis"],
    )
    fig.update_yaxes(gridcolor=PALETTE["grid"], zeroline=False, showline=False, color=PALETTE["muted"], automargin=True)
    return fig


def _plan_line(x, y, name: str, hover: str) -> go.Scatter:
    return go.Scatter(
        x=x, y=y, name=name, mode="lines",
        line=dict(color=PALETTE["blue"], width=2, dash="dash", shape="spline", smoothing=0.6),
        hovertemplate=hover,
    )


def _actual_line(x, y, name: str, hover: str, color: str | None = None) -> go.Scatter:
    color = color or PALETTE["green"]
    return go.Scatter(
        x=x, y=y, name=name, mode="lines+markers",
        line=dict(color=color, width=2.5, shape="spline", smoothing=0.6),
        marker=dict(size=6, color=PALETTE["bg"], line=dict(color=color, width=2)),
        fill="tozeroy", fillcolor=_fill(color, 0.10),
        hovertemplate=hover,
    )


def line_bar_chart(frame, metric: str, title: str, yaxis_tickformat: str | None = None) -> go.Figure:
    value_fmt = "%{y:.1%}" if yaxis_tickformat and "%" in yaxis_tickformat else "%{y:,.0f}"
    fig = go.Figure()
    fig.add_trace(_actual_line(frame["period"], frame[f"{metric}_actual"], "Actual", f"Actual: {value_fmt}<extra></extra>"))
    fig.add_trace(_plan_line(frame["period"], frame[f"{metric}_plan"], "Plan", f"Plan: {value_fmt}<extra></extra>"))
    if yaxis_tickformat:
        fig.update_yaxes(tickformat=yaxis_tickformat)
    return _style(fig, title)


def variance_combo(frame, metric: str, title: str) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    variance = frame[f"{metric}_variance"]
    fig.add_bar(
        x=frame["period"],
        y=variance,
        name="Variance $",
        marker=dict(
            color=[_fill(PALETTE["green"] if (v or 0) >= 0 else PALETTE["red"], 0.75) for v in variance.fillna(0)],
            cornerradius=4,
        ),
        hovertemplate="Variance: %{y:,.0f}<extra></extra>",
    )
    fig.add_scatter(
        x=frame["period"],
        y=frame[f"{metric}_variance_pct"],
        name="Variance %",
        mode="lines+markers",
        line=dict(color=PALETTE["blue"], width=2, shape="spline", smoothing=0.6),
        marker=dict(size=5),
        secondary_y=True,
        hovertemplate="Variance %%: %{y:.1%}<extra></extra>",
    )
    _style(fig, title)
    fig.update_yaxes(tickformat=".0%", secondary_y=True, showgrid=False)
    return fig


def scenario_cash_chart(scenarios: dict[str, object], safety_threshold: float) -> go.Figure:
    fig = go.Figure()
    fig.add_hrect(y0=-10000000, y1=safety_threshold, fillcolor=_fill(PALETTE["red"], 0.06), line_width=0, layer="below")
    fig.add_hline(
        y=safety_threshold, line_dash="dot", line_width=1, line_color=PALETTE["red"],
        annotation_text=f"Cash threshold ${safety_threshold:,.0f}", annotation_position="bottom left",
        annotation_font=dict(color=PALETTE["red"], size=11),
    )
    for name, frame in scenarios.items():
        color = SCENARIO_COLORS.get(name, PALETTE["muted"])
        fig.add_scatter(
            x=frame["period"],
            y=frame["cash_balance"],
            name=name,
            mode="lines",
            line=dict(width=2.5, color=color, shape="spline", smoothing=0.6),
            hovertemplate=f"{name}: %{{y:,.0f}}<extra></extra>",
        )
    values = [v for frame in scenarios.values() for v in frame["cash_balance"].dropna()]
    if values:
        low, high = min(min(values), safety_threshold), max(max(values), safety_threshold)
        pad = (high - low) * 0.08 or 1000
        fig.update_yaxes(range=[low - pad, high + pad])
    return _style(fig, "Cash Balance Projection")


def operating_metrics_chart(frame, metric: str, title: str, color: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(_actual_line(frame["period"], frame[metric], title, "%{y:,.2f}<extra></extra>", color=color))
    fig = _style(fig, title)
    fig.update_layout(showlegend=False)
    return fig


def multi_scenario_metric_chart(scenarios: dict[str, object], metric: str, title: str) -> go.Figure:
    fig = go.Figure()
    for name, frame in scenarios.items():
        color = SCENARIO_COLORS.get(name, PALETTE["muted"])
        fig.add_scatter(
            x=frame["period"],
            y=frame[metric],
            name=name,
            mode="lines",
            line=dict(width=2.5, color=color, shape="spline", smoothing=0.6),
            hovertemplate=f"{name}: %{{y:,.0f}}<extra></extra>",
        )
    return _style(fig, title)


def margin_trend_chart(frame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(_actual_line(frame["period"], frame["gross_margin_pct_actual"], "Actual", "Actual: %{y:.1%}<extra></extra>"))
    fig.add_trace(_plan_line(frame["period"], frame["gross_margin_pct_plan"], "Plan", "Plan: %{y:.1%}<extra></extra>"))
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
            x=["Revenue", "COGS", "Payroll", "OpEx", "Draws", "Loans", "Cash flow"],
            y=values,
            connector={"line": {"color": PALETTE["axis"], "dash": "dot", "width": 1}},
            increasing={"marker": {"color": _fill(PALETTE["green"], 0.85)}},
            decreasing={"marker": {"color": _fill(PALETTE["red"], 0.80)}},
            totals={"marker": {"color": _fill(PALETTE["blue"], 0.90)}},
            hovertemplate="%{x}: %{y:,.0f}<extra></extra>",
        )
    )
    fig = _style(fig, "Revenue to Cash Flow")
    fig.update_layout(showlegend=False, hovermode="closest")
    fig.update_xaxes(showspikes=False)
    return fig
