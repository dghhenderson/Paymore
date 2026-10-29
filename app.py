from __future__ import annotations

import pandas as pd
import streamlit as st

from paymore_dashboard.actuals import REQUIRED_COLUMNS, OPTIONAL_COLUMNS, actuals_template, load_actuals_upload, normalize_actuals, sample_actuals
from paymore_dashboard.charts import SCENARIO_COLORS, line_bar_chart, margin_trend_chart, multi_scenario_metric_chart, operating_metrics_chart, scenario_cash_chart, variance_combo, waterfall_chart
from paymore_dashboard.ingestion.pro_forma_parser import parse_pro_forma_workbook
from paymore_dashboard.models import DEFAULT_PRO_FORMA
from paymore_dashboard.planning import align_plan, blend_actuals_to_plan, build_comparison, current_month_projection, evaluate_cash_flags, project_scenario, scenario_summary_table, summarize_scenario, variance_table, year_run_rate_projection
from paymore_dashboard.ui.theme import TOKENS, inject_theme


CURRENT_DATE = pd.Timestamp("2026-03-20")
METRIC_LABELS = {
    "revenue": "Revenue",
    "gross_margin_pct": "Gross margin",
    "gross_profit": "Gross profit",
    "payroll": "Payroll",
    "net_operating_profit": "Operating profit",
    "cash_flow": "Cash flow",
    "cash_balance": "Cash balance",
}

st.set_page_config(page_title="PayMore Chinook Command", page_icon=":material/monitoring:", layout="wide")
inject_theme()


@st.cache_data(show_spinner=False)
def _load_budget(path_str: str):
    return parse_pro_forma_workbook(path_str)


def _plot(fig, key: str) -> None:
    with st.container(border=True, key=f"card_{key}"):
        st.plotly_chart(fig, width="stretch", theme=None, key=key, config={"displayModeBar": False})


def _html(markup: str) -> None:
    # Strip indentation so Markdown never treats the HTML as a code block.
    st.markdown("".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def _rows(items: list[tuple[str, str]]) -> str:
    return "".join(f'<div class="pm-row"><span>{label}</span><span>{value}</span></div>' for label, value in items)


def _stats(items: list[tuple[str, str]], cols: int = 2) -> str:
    cells = "".join(
        f'<div class="pm-stat"><div class="pm-stat-label">{label}</div><div class="pm-stat-value">{value}</div></div>'
        for label, value in items
    )
    return f'<div class="pm-stats{" cols-1" if cols == 1 else ""}">{cells}</div>'


def _sparkline(values, color: str, width: int = 96, height: int = 32) -> str:
    points = [float(v) for v in pd.to_numeric(pd.Series(values), errors="coerce").dropna()]
    if len(points) < 2:
        return ""
    low, high = min(points), max(points)
    span = (high - low) or 1.0
    step = width / (len(points) - 1)
    coords = [(i * step, height - 3 - (v - low) / span * (height - 6)) for i, v in enumerate(points)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = f"0,{height} {line} {width},{height}"
    last_x, last_y = coords[-1]
    return (
        f'<svg class="pm-spark" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none">'
        f'<polygon points="{area}" fill="{color}" fill-opacity="0.12"/>'
        f'<polyline points="{line}" stroke="{color}" stroke-width="1.75" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.5" fill="{color}"/>'
        "</svg>"
    )


def _currency(value) -> str:
    if pd.isna(value):
        return "n/a"
    return f"-${abs(value):,.0f}" if value < 0 else f"${value:,.0f}"


def _pct(value) -> str:
    return "n/a" if pd.isna(value) else f"{value:.1%}"


def _num(value) -> str:
    return "n/a" if pd.isna(value) else f"{value:,.1f}"


def _month(value) -> str:
    return "n/a" if value is None or pd.isna(value) else pd.Timestamp(value).strftime("%b %Y")


def _first_numeric(series: pd.Series, fallback: float) -> float:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    return float(cleaned.iloc[0]) if not cleaned.empty else fallback


def _scenario_inputs(column, name: str, defaults: dict[str, float]) -> dict[str, float]:
    with column, st.container(border=True, key=f"card_inputs_{name.replace(' ', '_')}"):
        _html(
            f'<div class="pm-scenario-head"><span class="pm-scenario-dot" style="--tone:{SCENARIO_COLORS.get(name, TOKENS["muted"])};"></span>'
            f'<span class="pm-scenario-name">{name}</span></div>'
        )
        revenue_change_pct = st.slider("Revenue growth %", -0.40, 0.40, float(defaults["revenue_change_pct"]), 0.01, key=f"{name}_revenue_change_pct")
        gross_margin_pct = st.slider("Gross margin %", 0.10, 0.80, float(defaults["gross_margin_pct"]), 0.01, key=f"{name}_gross_margin_pct")
        staff_count = st.number_input("Number of staff", min_value=1, value=int(defaults["staff_count"]), step=1, key=f"{name}_staff_count")
        payroll = st.number_input("Payroll cost", min_value=0.0, value=float(defaults["payroll"]), step=250.0, key=f"{name}_payroll")
        sales_change_pct = st.slider("Number of sales change %", -0.40, 0.50, float(defaults["sales_change_pct"]), 0.01, key=f"{name}_sales_change_pct")
        purchase_change_pct = st.slider("Number of purchases change %", -0.40, 0.50, float(defaults["purchase_change_pct"]), 0.01, key=f"{name}_purchase_change_pct")
        avg_sale_value = st.number_input("Average sale value", min_value=0.0, value=float(defaults["avg_sale_value"]), step=5.0, key=f"{name}_avg_sale_value")
        avg_purchase_value = st.number_input("Average purchase value", min_value=0.0, value=float(defaults["avg_purchase_value"]), step=10.0, key=f"{name}_avg_purchase_value")
        advertising_spend = st.number_input("Advertising spend", min_value=0.0, value=float(defaults["advertising_spend"]), step=100.0, key=f"{name}_advertising_spend")
        owner_draws = st.number_input("Owner draws", min_value=0.0, value=float(defaults["owner_draws"]), step=250.0, key=f"{name}_owner_draws")
        safety_threshold = st.number_input("Cash safety threshold", min_value=0.0, value=float(defaults["cash_safety_threshold"]), step=1000.0, key=f"{name}_cash_safety_threshold")
        return {
            "revenue_change_pct": revenue_change_pct,
            "gross_margin_pct": gross_margin_pct,
            "staff_count": float(staff_count),
            "hours_per_staff": 160.0,
            "payroll": payroll,
            "sales_change_pct": sales_change_pct,
            "purchase_change_pct": purchase_change_pct,
            "avg_sale_value": avg_sale_value,
            "avg_purchase_value": avg_purchase_value,
            "advertising_spend": advertising_spend,
            "owner_draws": owner_draws,
            "loan_payments": defaults["loan_payments"],
            "cash_safety_threshold": safety_threshold,
        }


def _scenario_draw_warning(plan: pd.DataFrame, actuals: pd.DataFrame, assumptions: dict[str, float]) -> bool:
    with_draw = project_scenario(plan, actuals, CURRENT_DATE, assumptions)
    no_draw_assumptions = {**assumptions, "owner_draws": 0.0}
    without_draw = project_scenario(plan, actuals, CURRENT_DATE, no_draw_assumptions)
    with_draw_flags = evaluate_cash_flags(with_draw, assumptions["cash_safety_threshold"])
    without_draw_flags = evaluate_cash_flags(without_draw, assumptions["cash_safety_threshold"])
    return with_draw_flags.required_injection > without_draw_flags.required_injection


TONE_LABELS = {
    TOKENS["positive"]: "On track",
    TOKENS["warning"]: "Watch",
    TOKENS["negative"]: "At risk",
}


def _metric_card(label: str, value: str, tone: str, plan_label: str, plan_value: str, delta: str | None = None, spark=None) -> None:
    status = TONE_LABELS.get(tone, "Watch")
    badge = delta or status
    _html(
        f"""
        <div class="pm-card pm-kpi">
            <div class="pm-kpi-top">
                <div class="pm-eyebrow">{label}</div>
                <span class="pm-badge" style="--tone:{tone};" title="{status}">{badge}</span>
            </div>
            <div class="pm-kpi-value">{value}</div>
            <div class="pm-kpi-foot">
                <div class="pm-kpi-plan">{plan_label} <b>{plan_value}</b></div>
                {_sparkline(spark, tone) if spark is not None else ""}
            </div>
        </div>
        """
    )


def _delta(actual, plan, as_points: bool = False) -> str | None:
    if pd.isna(actual) or pd.isna(plan) or (not as_points and not plan):
        return None
    if as_points:
        change = (actual - plan) * 100
        return f"{'▲' if change >= 0 else '▼'} {abs(change):.1f} pts"
    change = (actual - plan) / abs(plan)
    return f"{'▲' if change >= 0 else '▼'} {abs(change):.0%}"


def _status_tone(actual, plan, invert: bool = False) -> str:
    if pd.isna(actual) or pd.isna(plan):
        return TOKENS["warning"]
    good = actual >= plan if not invert else actual <= plan
    gap = abs(actual - plan) / abs(plan) if plan not in (0, None) else 0
    if good:
        return TOKENS["positive"]
    if gap <= 0.1:
        return TOKENS["warning"]
    return TOKENS["negative"]


def _performance_summary(row) -> str:
    revenue_var = row.get("revenue_variance", 0) or 0
    margin_var = row.get("gross_margin_pct_variance", 0) or 0
    payroll_var = row.get("payroll_variance", 0) or 0
    drivers = []
    if revenue_var < 0:
        drivers.append(f"revenue is {_currency(abs(revenue_var))} below plan")
    elif revenue_var > 0:
        drivers.append(f"revenue is {_currency(revenue_var)} ahead of plan")
    if margin_var < 0:
        drivers.append(f"margin is trailing by {_pct(abs(margin_var))}")
    elif margin_var > 0:
        drivers.append(f"margin is ahead by {_pct(margin_var)}")
    if payroll_var > 0:
        drivers.append(f"payroll is {_currency(payroll_var)} over target")
    elif payroll_var < 0:
        drivers.append(f"payroll is {_currency(abs(payroll_var))} under target")
    direction = "ahead of plan" if revenue_var >= 0 and margin_var >= 0 and payroll_var <= 0 else "behind plan"
    reason = ", ".join(drivers[:3]) if drivers else "performance is broadly in line with the pro forma"
    return f"The store is currently {direction} in March 2026 because {reason}."


def _insights_block(row, current_projection, base_flags, safety_threshold) -> list[tuple[str, str, str]]:
    revenue_pct = row.get("revenue_variance_pct")
    margin_points = row.get("gross_margin_pct_variance")
    revenue_sentence = (
        f"Revenue is currently {abs(revenue_pct) * 100:.0f} percent {'below' if revenue_pct < 0 else 'above'} plan."
        if pd.notna(revenue_pct)
        else "Revenue versus plan is not yet available."
    )
    margin_sentence = (
        f"Margin is {abs(margin_points) * 100:.1f} points {'above' if margin_points > 0 else 'below'} plan."
        if pd.notna(margin_points)
        else "Margin versus plan is not yet available."
    )
    run_rate_sentence = (
        f"At current run rate the store will end March at {_currency(current_projection['projected_month_revenue'])} versus a projected {_currency(row.get('revenue_plan'))}."
    )
    cash_sentence = (
        f"At the current scenario the business stays above the cash threshold of {_currency(safety_threshold)} and owners could begin taking modest draws in {_month(base_flags.safe_draw_month)}."
        if base_flags.safe_draw_month
        else f"At the current scenario the business does not yet support owner draws while holding the cash threshold of {_currency(safety_threshold)}."
    )
    def tone(good) -> str:
        if good is None:
            return TOKENS["warning"]
        return TOKENS["positive"] if good else TOKENS["negative"]

    on_pace = current_projection["projected_month_revenue"] >= (row.get("revenue_plan") or 0)
    return [
        (tone(None if pd.isna(revenue_pct) else revenue_pct >= 0), "$", revenue_sentence),
        (tone(None if pd.isna(margin_points) else margin_points >= 0), "%", margin_sentence),
        (tone(on_pace), "↗" if on_pace else "↘", run_rate_sentence),
        (tone(bool(base_flags.safe_draw_month)), "◆", cash_sentence),
    ]


_html(
    f"""
    <div class="pm-header">
        <div class="pm-brand-row">
            <div class="pm-logo">P</div>
            <div>
                <div class="pm-title">PayMore Chinook <span style="color:{TOKENS['muted']};font-weight:500;">Command</span></div>
                <div class="pm-subtitle">Sales, margin, staffing and cash, measured against the pro forma.</div>
            </div>
        </div>
        <div class="pm-chips">
            <span class="pm-chip">Store AB01</span>
            <span class="pm-chip">As of {CURRENT_DATE.strftime('%b %-d, %Y')}</span>
            <span class="pm-chip is-accent"><span class="pm-live"></span>Scenario ready</span>
        </div>
    </div>
    """
)

sidebar = st.sidebar
sidebar.markdown("## Data")
sidebar.caption(f"Pro forma: `{DEFAULT_PRO_FORMA.name}` (built in). Upload a PayMore sales report to override actuals.")
actuals_upload = sidebar.file_uploader("PayMore sales report or actuals CSV/XLSX", type=["csv", "xlsx"])

budget = _load_budget(str(DEFAULT_PRO_FORMA))
plan = align_plan(budget.monthly_budget)
default_actuals = sample_actuals(budget.monthly_actuals)

upload_error = None
try:
    uploaded_actuals = load_actuals_upload(actuals_upload, default_actuals)
except ValueError as exc:
    upload_error = str(exc)
    uploaded_actuals = default_actuals.copy()

actuals_editor = sidebar.checkbox("Edit actuals in app", value=True)
actuals_frame = uploaded_actuals.copy()

sidebar.markdown("### Base assumptions")
safety_threshold = sidebar.number_input("Safety cash threshold", min_value=0.0, value=20000.0, step=1000.0)
march_plan = plan.loc[plan["period"] == pd.Timestamp("2026-03-01")] if not plan.empty else pd.DataFrame()
base_margin = _first_numeric(march_plan["gross_margin_pct"] if "gross_margin_pct" in march_plan else pd.Series(dtype="float64"), 0.4)
base_payroll = _first_numeric(march_plan["payroll"] if "payroll" in march_plan else pd.Series(dtype="float64"), 9500.0)
base_sales = _first_numeric(march_plan["sales_count"] if "sales_count" in march_plan else pd.Series(dtype="float64"), 90.0)
base_purchases = _first_numeric(march_plan["purchase_count"] if "purchase_count" in march_plan else pd.Series(dtype="float64"), 55.0)
base_avg_sale = _first_numeric(march_plan["avg_sale_value"] if "avg_sale_value" in march_plan else pd.Series(dtype="float64"), 245.0)
base_avg_purchase = _first_numeric(march_plan["avg_purchase_value"] if "avg_purchase_value" in march_plan else pd.Series(dtype="float64"), 700.0)

sidebar.markdown("### Global defaults")
loan_payments = sidebar.number_input("Monthly loan payments", min_value=0.0, value=0.0, step=100.0)

if actuals_editor:
    with st.expander("Edit monthly actuals", expanded=False, icon=":material/table_edit:"):
        st.markdown("Enter monthly numbers from the PayMore dashboard here, or upload a CSV/XLSX from the sidebar. Charts update immediately from the values below.")
        st.caption("Default sample data is included for January, February, and March 2026.")
        if upload_error:
            st.error(f"Uploaded actuals file could not be used: {upload_error}")
        st.markdown(
            "**Required columns:** "
            + ", ".join(f"`{column}`" for column in REQUIRED_COLUMNS)
            + "  \n**Optional columns:** "
            + ", ".join(f"`{column}`" for column in OPTIONAL_COLUMNS)
        )
        editable = actuals_frame.copy()
        editable = editable.rename(
            columns={
                "period": "month",
                "gross_margin_pct": "gross_margin_percent",
                "loan_payments": "loan_payment",
                "avg_sale_value": "average_sale_value",
                "avg_purchase_value": "average_purchase_value",
            }
        )
        editable["month"] = pd.to_datetime(editable["month"]).dt.strftime("%Y-%m-%d")
        editable = editable[[*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS]]
        edited = st.data_editor(editable, width="stretch", num_rows="dynamic", hide_index=True)
        try:
            actuals = normalize_actuals(edited)
            st.success("Actuals loaded successfully. Charts and KPI cards are using the current table values.")
        except ValueError as exc:
            st.error(f"Actuals input needs attention: {exc}")
            actuals = default_actuals.copy()
            fallback = actuals_template(default_actuals)
            st.caption("Showing the default workbook actuals until the input table is corrected.")
            st.dataframe(fallback, width="stretch", hide_index=True)
else:
    actuals = actuals_frame

comparison = build_comparison(plan, actuals)
comparison_display = blend_actuals_to_plan(comparison, CURRENT_DATE, months_to_blend=3)
current_projection = current_month_projection(comparison, CURRENT_DATE)
year_projection = year_run_rate_projection(comparison, CURRENT_DATE)

scenario_defaults = {
    "Best Case": {
        "revenue_change_pct": 0.10,
        "gross_margin_pct": min(base_margin + 0.03, 0.8),
        "staff_count": 4,
        "hours_per_staff": 160.0,
        "payroll": base_payroll,
        "sales_change_pct": 0.08,
        "purchase_change_pct": 0.03,
        "avg_sale_value": base_avg_sale * 1.03,
        "avg_purchase_value": base_avg_purchase * 0.98,
        "advertising_spend": 1200.0,
        "owner_draws": 0.0,
        "loan_payments": loan_payments,
        "cash_safety_threshold": safety_threshold,
    },
    "Medium Case": {
        "revenue_change_pct": 0.0,
        "gross_margin_pct": base_margin,
        "staff_count": 4,
        "hours_per_staff": 160.0,
        "payroll": base_payroll,
        "sales_change_pct": 0.0,
        "purchase_change_pct": 0.0,
        "avg_sale_value": base_avg_sale,
        "avg_purchase_value": base_avg_purchase,
        "advertising_spend": 1500.0,
        "owner_draws": 0.0,
        "loan_payments": loan_payments,
        "cash_safety_threshold": safety_threshold,
    },
    "Worst Case": {
        "revenue_change_pct": -0.12,
        "gross_margin_pct": max(base_margin - 0.04, 0.1),
        "staff_count": 5,
        "hours_per_staff": 160.0,
        "payroll": base_payroll * 1.08,
        "sales_change_pct": -0.10,
        "purchase_change_pct": 0.06,
        "avg_sale_value": base_avg_sale * 0.97,
        "avg_purchase_value": base_avg_purchase * 1.04,
        "advertising_spend": 1800.0,
        "owner_draws": 0.0,
        "loan_payments": loan_payments,
        "cash_safety_threshold": safety_threshold,
    },
}
initial_scenario_frames = {
    name: project_scenario(plan, actuals, CURRENT_DATE, defaults)
    for name, defaults in scenario_defaults.items()
}
initial_scenario_flags = {
    name: evaluate_cash_flags(frame, scenario_defaults[name]["cash_safety_threshold"])
    for name, frame in initial_scenario_frames.items()
}
base_flags = initial_scenario_flags["Medium Case"]
current_month = CURRENT_DATE.to_period("M").to_timestamp()
current_row = comparison.loc[comparison["period"] == current_month]
current_row = current_row.iloc[0] if not current_row.empty else comparison.iloc[0]
owner_draw_status = "Safe to draw" if base_flags.safe_draw_month and base_flags.safe_draw_month <= current_month else "Hold draws"
annualized_run_rate = current_projection["projected_month_revenue"] * 12
summary_sentence = _performance_summary(current_row)
insights = _insights_block(current_row, current_projection, base_flags, safety_threshold)

current_cash = actuals["cash_balance"].iloc[-1] if not actuals.empty else 0
cash_tone = TOKENS["positive"] if current_cash >= safety_threshold else TOKENS["negative"]
forecast_tone = TOKENS["positive"] if current_projection["projected_month_revenue"] >= (current_row.get("revenue_plan") or 0) else TOKENS["negative"]
history = comparison_display.loc[comparison_display["period"] <= current_month]
cash_history = actuals["cash_balance"] if "cash_balance" in actuals else None

overview_cards = st.columns(4)
with overview_cards[0]:
    _metric_card(
        "Revenue · MTD", _currency(current_row.get("revenue_actual")),
        _status_tone(current_row.get("revenue_actual"), current_row.get("revenue_plan")),
        "Plan", _currency(current_row.get("revenue_plan")),
        _delta(current_row.get("revenue_actual"), current_row.get("revenue_plan")),
        history.get("revenue_display"),
    )
with overview_cards[1]:
    _metric_card(
        "Gross margin", _pct(current_row.get("gross_margin_pct_actual")),
        _status_tone(current_row.get("gross_margin_pct_actual"), current_row.get("gross_margin_pct_plan")),
        "Plan", _pct(current_row.get("gross_margin_pct_plan")),
        _delta(current_row.get("gross_margin_pct_actual"), current_row.get("gross_margin_pct_plan"), as_points=True),
        history.get("gross_margin_pct_display"),
    )
with overview_cards[2]:
    _metric_card(
        "Cash balance", _currency(current_cash), cash_tone,
        "Threshold", _currency(safety_threshold),
        _delta(current_cash, safety_threshold),
        cash_history,
    )
with overview_cards[3]:
    _metric_card(
        "Month forecast", _currency(current_projection["projected_month_revenue"]), forecast_tone,
        "Plan", _currency(current_row.get("revenue_plan")),
        _delta(current_projection["projected_month_revenue"], current_row.get("revenue_plan")),
    )

tabs = st.tabs([
    ":material/dashboard: Overview",
    ":material/compare_arrows: Actual vs Pro Forma",
    ":material/tune: Scenarios",
    ":material/account_balance_wallet: Cash Planning",
    ":material/storefront: Operating Metrics",
])

with tabs[0]:
    hero_left, hero_mid, hero_right = st.columns([1.15, 1.0, 0.75])
    with hero_left:
        _html(
            f"""
            <div class="pm-card pm-hero">
                <div class="pm-eyebrow">Executive summary</div>
                <div class="pm-hero-text">{summary_sentence}</div>
                <div class="pm-hero-note">Current actuals measured against the pro forma baseline.</div>
            </div>
            """
        )
    with hero_mid:
        insight_markup = "".join(
            f'<div class="pm-insight"><span class="pm-insight-icon" style="--tone:{tone};">{icon}</span><span>{text}</span></div>'
            for tone, icon, text in insights
        )
        _html(f'<div class="pm-card"><div class="pm-eyebrow">Insights</div><div style="margin-top:.4rem;">{insight_markup}</div></div>')
    with hero_right:
        _html(
            f"""
            <div class="pm-card pm-runrate">
                <div class="pm-eyebrow">Annualized run rate</div>
                <div class="pm-big">{_currency(annualized_run_rate)}</div>
                <div class="pm-hero-note">From {CURRENT_DATE.strftime('%B %Y')} actuals to date.</div>
                <div style="margin-top:1rem;">{_stats([("Full-year revenue", _currency(year_projection["projected_year_revenue"])), ("Full-year profit", _currency(year_projection["projected_year_profit"]))], cols=1)}</div>
            </div>
            """
        )
    st.write("")

    row_one = st.columns(2)
    with row_one[0]:
        overview_revenue = comparison_display.copy()
        overview_revenue["revenue_actual"] = overview_revenue["revenue_display"]
        _plot(line_bar_chart(overview_revenue, "revenue", "Revenue vs Plan"), "overview_revenue_vs_plan")
    with row_one[1]:
        overview_margin = comparison_display.copy()
        overview_margin["gross_margin_pct_actual"] = overview_margin["gross_margin_pct_display"]
        _plot(margin_trend_chart(overview_margin), "overview_margin_vs_plan")

    row_two = st.columns([0.95, 1.05])
    with row_two[0]:
        with st.container(border=True, key="card_runrate"):
            _html('<div class="pm-section-title">Run-rate snapshot</div><div class="pm-section-sub">Medium case, current month and full year.</div>')
            _html(
                _stats(
                    [
                        ("Month revenue", _currency(current_projection["projected_month_revenue"])),
                        ("Month profit", _currency(current_projection["projected_month_profit"])),
                        ("Full-year revenue", _currency(year_projection["projected_year_revenue"])),
                        ("Full-year profit", _currency(year_projection["projected_year_profit"])),
                    ]
                )
            )
            _html(
                '<div style="margin-top:.8rem;">'
                + _rows(
                    [
                        ("First positive cash flow month", _month(base_flags.positive_cash_flow_month)),
                        ("Capital injection month", _month(base_flags.first_injection_month)),
                        ("Required injection", _currency(base_flags.required_injection)),
                        ("Earliest safe owner draw", _month(base_flags.safe_draw_month)),
                        ("Suggested monthly draw", _currency(base_flags.suggested_draw)),
                    ]
                )
                + "</div>"
            )
            st.caption("Positive cash flow month: first month net cash flow turns positive and stays positive. Safe owner draw: a recurring draw that keeps projected cash above the threshold every month after.")
    with row_two[1]:
        _plot(waterfall_chart(current_row), "overview_revenue_to_cashflow")

with tabs[1]:
    metric_for_table = st.segmented_control(
        "Variance metric",
        options=["revenue", "gross_margin_pct", "payroll", "net_operating_profit", "cash_flow"],
        format_func=lambda m: METRIC_LABELS.get(m, m),
        default="revenue",
        key="variance_metric",
    ) or "revenue"
    chart_row_1 = st.columns(2)
    with chart_row_1[0]:
        revenue_chart = comparison_display.copy()
        revenue_chart["revenue_actual"] = revenue_chart["revenue_display"]
        _plot(line_bar_chart(revenue_chart, "revenue", "Revenue vs Plan"), "actuals_revenue_vs_plan")
    with chart_row_1[1]:
        margin_chart_frame = comparison_display.copy()
        margin_chart_frame["gross_margin_pct_actual"] = margin_chart_frame["gross_margin_pct_display"]
        _plot(line_bar_chart(margin_chart_frame, "gross_margin_pct", "Margin vs Plan", ".0%"), "actuals_margin_vs_plan")

    chart_row_2 = st.columns(2)
    with chart_row_2[0]:
        payroll_chart = comparison_display.copy()
        payroll_chart["payroll_actual"] = payroll_chart["payroll_display"]
        _plot(line_bar_chart(payroll_chart, "payroll", "Payroll vs Plan"), "actuals_payroll_vs_plan")
    with chart_row_2[1]:
        nop_chart = comparison_display.copy()
        nop_chart["net_operating_profit_actual"] = nop_chart["net_operating_profit_display"]
        _plot(line_bar_chart(nop_chart, "net_operating_profit", "Operating Profit vs Plan"), "actuals_operating_profit_vs_plan")

    chart_row_3 = st.columns(2)
    with chart_row_3[0]:
        cashflow_chart = comparison_display.copy()
        cashflow_chart["cash_flow_actual"] = cashflow_chart["cash_flow_display"]
        _plot(line_bar_chart(cashflow_chart, "cash_flow", "Cash Flow vs Plan"), "actuals_cashflow_vs_plan")
    with chart_row_3[1]:
        _plot(variance_combo(comparison, metric_for_table, "Variance to Plan"), "actuals_variance_to_plan")

    with st.container(border=True, key="card_variance_table"):
        _html('<div class="pm-section-title">Variance table</div>')
        variance_df = variance_table(comparison, metric_for_table)
        if "Variance %" in variance_df.columns:
            variance_df["Variance %"] = variance_df["Variance %"].map(lambda value: "—" if pd.isna(value) else f"{value:.1%}")
        if "Month" in variance_df.columns:
            variance_df["Month"] = variance_df["Month"].map(_month)
        value_format = _pct if metric_for_table.endswith("_pct") else _currency
        for column in ["Actual", "Projected", "Variance"]:
            if column in variance_df.columns:
                variance_df[column] = variance_df[column].map(lambda value: "—" if pd.isna(value) else value_format(value))
        st.dataframe(variance_df, width="stretch", hide_index=True)

with tabs[2]:
    _html(
        '<div class="pm-section-title" style="font-size:1.15rem;">Scenario engine</div>'
        '<div class="pm-section-sub">Adjust the levers for each case. Revenue, margin, staffing, cash flow, capital injection and owner draw timing all recalculate.</div>'
    )
    input_cols = st.columns(3)
    scenario_assumptions = {
        "Best Case": _scenario_inputs(input_cols[0], "Best Case", scenario_defaults["Best Case"]),
        "Medium Case": _scenario_inputs(input_cols[1], "Medium Case", scenario_defaults["Medium Case"]),
        "Worst Case": _scenario_inputs(input_cols[2], "Worst Case", scenario_defaults["Worst Case"]),
    }
    scenario_frames = {
        name: project_scenario(plan, actuals, CURRENT_DATE, assumptions)
        for name, assumptions in scenario_assumptions.items()
    }
    scenario_flags = {
        name: evaluate_cash_flags(scenario_frames[name], scenario_assumptions[name]["cash_safety_threshold"])
        for name in scenario_frames.keys()
    }
    draw_warnings = {
        name: _scenario_draw_warning(plan, actuals, scenario_assumptions[name])
        for name in scenario_assumptions.keys()
    }
    scenario_summaries = [
        summarize_scenario(name, scenario_frames[name], scenario_assumptions[name]["cash_safety_threshold"])
        for name in ["Best Case", "Medium Case", "Worst Case"]
    ]
    summary_cols = st.columns(3)
    for idx, summary in enumerate(scenario_summaries):
        with summary_cols[idx]:
            warning = (
                '<div class="pm-callout">This owner draw level means the business needs extra capital.</div>'
                if draw_warnings[summary.scenario]
                else ""
            )
            _html(
                f"""
                <div class="pm-card">
                    <div class="pm-scenario-head">
                        <span class="pm-scenario-dot" style="--tone:{SCENARIO_COLORS.get(summary.scenario, TOKENS['muted'])};"></span>
                        <span class="pm-scenario-name">{summary.scenario}</span>
                    </div>
                    {_stats([("Monthly revenue", _currency(summary.monthly_revenue)), ("Ending cash", _currency(summary.ending_cash_balance))])}
                    <div style="margin-top:.7rem;">
                    {_rows([
                        ("Gross profit / mo", _currency(summary.monthly_gross_profit)),
                        ("Operating profit / mo", _currency(summary.monthly_operating_profit)),
                        ("Net cash flow / mo", _currency(summary.monthly_net_cash_flow)),
                        ("First positive cash flow", _month(summary.positive_cash_flow_month)),
                        ("Below threshold", _month(summary.threshold_breach_month)),
                        ("Capital injection", _currency(summary.capital_injection_needed)),
                        ("Earliest safe draw", _month(summary.safe_distribution_month)),
                        ("Suggested draw / mo", _currency(summary.suggested_monthly_distribution)),
                    ])}
                    </div>
                    {warning}
                </div>
                """
            )
    st.write("")

    chart_left, chart_right = st.columns([1.1, 0.9])
    with chart_left:
        _plot(scenario_cash_chart(scenario_frames, scenario_assumptions["Medium Case"]["cash_safety_threshold"]), "scenario_cash_projection")
    with chart_right:
        scenario_df = scenario_summary_table(scenario_summaries)
        for col in [
            "monthly_revenue",
            "monthly_gross_profit",
            "monthly_operating_profit",
            "monthly_net_cash_flow",
            "ending_cash_balance",
            "capital_injection_needed",
            "suggested_monthly_distribution",
        ]:
            scenario_df[col] = scenario_df[col].map(_currency)
        for col in ["positive_cash_flow_month", "threshold_breach_month", "safe_distribution_month"]:
            scenario_df[col] = scenario_df[col].map(_month)
        with st.container(border=True, key="card_scenario_table"):
            _html('<div class="pm-section-title">Scenario comparison</div>')
            table = scenario_df.set_index("scenario").T
            table.index = [label.replace("_", " ").capitalize() for label in table.index]
            st.dataframe(table, width="stretch")

    metric_choice = st.segmented_control(
        "Scenario chart metric",
        options=["revenue", "gross_profit", "net_operating_profit", "cash_flow", "cash_balance"],
        format_func=lambda m: METRIC_LABELS.get(m, m),
        default="revenue",
        key="scenario_metric_choice",
    ) or "revenue"
    scenario_metric_fig = multi_scenario_metric_chart(
        scenario_frames,
        metric_choice,
        f"Scenario lens: {METRIC_LABELS.get(metric_choice, metric_choice)}",
    )
    _plot(scenario_metric_fig, "scenario_metric_lens")

with tabs[3]:
    cash_left, cash_right = st.columns([1.25, 0.75])
    with cash_left:
        _plot(scenario_cash_chart(scenario_frames, safety_threshold), "cash_planning_projection")
    with cash_right:
        cash_table = pd.DataFrame(
            [
                {"Scenario": name, "Positive cash flow month": _month(flags.positive_cash_flow_month), "Injection month": _month(flags.first_injection_month), "Required injection": _currency(flags.required_injection), "Safe draw month": _month(flags.safe_draw_month), "Suggested draw": _currency(flags.suggested_draw), "Draw warning": "Owner draw triggers capital need" if draw_warnings[name] else "No draw warning"}
                for name, flags in scenario_flags.items()
            ]
        )
        for name, flags in scenario_flags.items():
            warning = '<div class="pm-callout">Owner draw triggers a capital need.</div>' if draw_warnings[name] else ""
            _html(
                f"""
                <div class="pm-card" style="margin-bottom:.75rem;">
                    <div class="pm-scenario-head">
                        <span class="pm-scenario-dot" style="--tone:{SCENARIO_COLORS.get(name, TOKENS['muted'])};"></span>
                        <span class="pm-scenario-name">{name}</span>
                    </div>
                    {_rows([
                        ("Positive cash flow", _month(flags.positive_cash_flow_month)),
                        ("Injection month", _month(flags.first_injection_month)),
                        ("Required injection", _currency(flags.required_injection)),
                        ("Safe draw month", _month(flags.safe_draw_month)),
                        ("Suggested draw", _currency(flags.suggested_draw)),
                    ])}
                    {warning}
                </div>
                """
            )
    with st.container(border=True, key="card_cash_table"):
        _html('<div class="pm-section-title">Cash planning table</div>')
        st.dataframe(cash_table, width="stretch", hide_index=True)

with tabs[4]:
    op_row_1 = st.columns(2)
    with op_row_1[0]:
        _plot(operating_metrics_chart(comparison, "sales_count_actual", "Sales Count by Month", "#34D399"), "ops_sales_count")
    with op_row_1[1]:
        _plot(operating_metrics_chart(comparison, "purchase_count_actual", "Purchase Count by Month", "#818CF8"), "ops_purchase_count")

    op_row_2 = st.columns(2)
    with op_row_2[0]:
        _plot(operating_metrics_chart(comparison, "avg_sale_value_actual", "Average Sale Value", "#FBBF24"), "ops_avg_sale_value")
    with op_row_2[1]:
        _plot(operating_metrics_chart(comparison, "avg_purchase_value_actual", "Average Purchase Value", "#C084FC"), "ops_avg_purchase_value")

    op_row_3 = st.columns(2)
    with op_row_3[0]:
        _plot(operating_metrics_chart(comparison, "sales_per_staff_hour_actual", "Sales per Staff Hour", "#F87171"), "ops_sales_per_staff_hour")
    with op_row_3[1]:
        _plot(operating_metrics_chart(comparison, "inventory_value_actual", "Inventory Value", "#38BDF8"), "ops_inventory_value")
