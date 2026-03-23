from __future__ import annotations

import pandas as pd
import streamlit as st

from paymore_dashboard.actuals import REQUIRED_COLUMNS, OPTIONAL_COLUMNS, actuals_template, load_actuals_upload, normalize_actuals, sample_actuals
from paymore_dashboard.charts import line_bar_chart, margin_trend_chart, multi_scenario_metric_chart, operating_metrics_chart, scenario_cash_chart, variance_combo, waterfall_chart
from paymore_dashboard.ingestion.pro_forma_parser import parse_pro_forma_workbook
from paymore_dashboard.models import DEFAULT_PRO_FORMA
from paymore_dashboard.planning import align_plan, blend_actuals_to_plan, build_comparison, current_month_projection, evaluate_cash_flags, project_scenario, scenario_summary_table, summarize_scenario, variance_table, year_run_rate_projection
from paymore_dashboard.ui.theme import inject_theme


CURRENT_DATE = pd.Timestamp("2026-03-20")

st.set_page_config(page_title="PayMore Chinook Operator Dashboard", page_icon=":bar_chart:", layout="wide")
inject_theme()
@st.cache_data(show_spinner=False)
def _load_budget(path_str: str):
    return parse_pro_forma_workbook(path_str)


def _currency(value) -> str:
    return "n/a" if pd.isna(value) else f"${value:,.0f}"


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
    with column:
        st.markdown(f"#### {name}")
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


def _metric_card(label: str, value: str, kicker: str, tone: str = "#54A52A") -> None:
    status_bg = "rgba(34,197,94,.12)"
    status_fg = "#22C55E"
    status = "On Track"
    if tone == "#F59E0B":
        status_bg = "rgba(245,158,11,.16)"
        status_fg = "#F59E0B"
        status = "Watch"
    if tone == "#EF4444":
        status_bg = "rgba(239,68,68,.14)"
        status_fg = "#EF4444"
        status = "Risk"
    st.markdown(
        f"""
        <div class="pm-metric" style="--card-accent:{tone};--status-bg:{status_bg};--status-fg:{status_fg};">
            <div class="pm-kicker">{kicker}</div>
            <div class="pm-value" style="color:{tone};">{value}</div>
            <div class="pm-label">{label}</div>
            <div class="pm-status"><span class="pm-dot"></span>{status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _status_tone(actual, plan, invert: bool = False) -> str:
    if pd.isna(actual) or pd.isna(plan):
        return "#F59E0B"
    good = actual >= plan if not invert else actual <= plan
    gap = abs(actual - plan) / abs(plan) if plan not in (0, None) else 0
    if good and gap <= 0.1:
        return "#22C55E"
    if good:
        return "#22C55E"
    if gap <= 0.1:
        return "#F59E0B"
    return "#EF4444"


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


def _insights_block(row, current_projection, base_flags, safety_threshold) -> list[str]:
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
    return [revenue_sentence, margin_sentence, run_rate_sentence, cash_sentence]


st.markdown(
    """
    <div class="pm-topbar">
        <div style="display:flex;justify-content:space-between;gap:1rem;align-items:center;flex-wrap:wrap;">
            <div>
                <div class="pm-brand">PayMore Chinook</div>
                <div style="color:#94A3B8;font-size:.95rem;max-width:52rem;">Retail operating dashboard for sales, margin, staffing, cash discipline, and store-level decisions.</div>
            </div>
            <div style="display:flex;gap:.65rem;flex-wrap:wrap;">
                <div style="padding:.65rem .95rem;background:#151A23;border-radius:12px;border:1px solid rgba(255,255,255,.08);color:#E5E7EB;font-weight:700;">AB01</div>
                <div style="padding:.65rem .95rem;background:#151A23;border-radius:12px;border:1px solid rgba(255,255,255,.08);color:#94A3B8;font-weight:700;">Retail Ops</div>
                <div style="padding:.65rem .95rem;background:#151A23;border-radius:12px;border:1px solid rgba(59,130,246,.24);color:#93C5FD;font-weight:700;">Scenario Ready</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

sidebar = st.sidebar
sidebar.markdown("## Inputs")
sidebar.caption("The pro forma is built into the app. Upload your PayMore sales report or edit monthly operating inputs below.")
sidebar.markdown(f"Using built-in pro forma: `{DEFAULT_PRO_FORMA.name}`")
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

sidebar.markdown("### Base Assumptions")
safety_threshold = sidebar.number_input("Safety cash threshold", min_value=0.0, value=20000.0, step=1000.0)
march_plan = plan.loc[plan["period"] == pd.Timestamp("2026-03-01")] if not plan.empty else pd.DataFrame()
base_margin = _first_numeric(march_plan["gross_margin_pct"] if "gross_margin_pct" in march_plan else pd.Series(dtype="float64"), 0.4)
base_payroll = _first_numeric(march_plan["payroll"] if "payroll" in march_plan else pd.Series(dtype="float64"), 9500.0)
base_sales = _first_numeric(march_plan["sales_count"] if "sales_count" in march_plan else pd.Series(dtype="float64"), 90.0)
base_purchases = _first_numeric(march_plan["purchase_count"] if "purchase_count" in march_plan else pd.Series(dtype="float64"), 55.0)
base_avg_sale = _first_numeric(march_plan["avg_sale_value"] if "avg_sale_value" in march_plan else pd.Series(dtype="float64"), 245.0)
base_avg_purchase = _first_numeric(march_plan["avg_purchase_value"] if "avg_purchase_value" in march_plan else pd.Series(dtype="float64"), 700.0)

sidebar.markdown("### Global Defaults")
loan_payments = sidebar.number_input("Monthly loan payments", min_value=0.0, value=0.0, step=100.0)

if actuals_editor:
    with st.expander("Actuals Input", expanded=False):
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
        edited = st.data_editor(editable, use_container_width=True, num_rows="dynamic", hide_index=True)
        try:
            actuals = normalize_actuals(edited)
            st.success("Actuals loaded successfully. Charts and KPI cards are using the current table values.")
        except ValueError as exc:
            st.error(f"Actuals input needs attention: {exc}")
            actuals = default_actuals.copy()
            fallback = actuals_template(default_actuals)
            st.caption("Showing the default workbook actuals until the input table is corrected.")
            st.dataframe(fallback, use_container_width=True, hide_index=True)
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

overview_cards = st.columns(4)
with overview_cards[0]:
    _metric_card("Revenue", _currency(current_row.get("revenue_actual")), "vs plan", _status_tone(current_row.get("revenue_actual"), current_row.get("revenue_plan")))
with overview_cards[1]:
    _metric_card("Gross Margin", _pct(current_row.get("gross_margin_pct_actual")), "vs plan", _status_tone(current_row.get("gross_margin_pct_actual"), current_row.get("gross_margin_pct_plan")))
current_cash = actuals['cash_balance'].iloc[-1] if not actuals.empty else 0
cash_tone = "#22C55E" if current_cash >= safety_threshold else "#EF4444"
forecast_tone = "#22C55E" if current_projection["projected_month_revenue"] >= (current_row.get("revenue_plan") or 0) else "#EF4444"
with overview_cards[2]:
    _metric_card("Cash Balance", _currency(current_cash), "threshold check", cash_tone)
with overview_cards[3]:
    _metric_card("Forecast Revenue", _currency(current_projection["projected_month_revenue"]), "run rate", forecast_tone)

tabs = st.tabs(["Overview", "Actual vs Pro Forma", "Scenarios", "Cash Planning", "Operating Metrics"])

with tabs[0]:
    hero_left, hero_mid, hero_right = st.columns([1.15, 0.9, 0.75])
    with hero_left:
        st.markdown(
            f"""
            <div class="pm-summary">
                <div style="font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:#94A3B8;">Executive Summary</div>
                <div style="font-size:1.4rem;font-weight:800;margin-top:.55rem;color:#F8FAFC;line-height:1.35;">{summary_sentence}</div>
                <div style="margin-top:.75rem;color:#94A3B8;">Built for day-to-day retail operating decisions using current actuals and the pro forma baseline.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hero_mid:
        insight_markup = "".join(
            f'<div style="padding:.5rem 0;border-bottom:1px solid rgba(148,163,184,0.14);color:#334155;">{line}</div>'
            for line in insights[:-1]
        ) + f'<div style="padding:.5rem 0;color:#334155;">{insights[-1]}</div>'
        st.markdown(
            f"""
            <div class="pm-panel">
                <div style="font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:#94A3B8;">Insights</div>
                <div style="margin-top:.45rem;">{insight_markup}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hero_right:
        st.markdown(
            f"""
            <div class="pm-runrate">
                <div style="font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:#93C5FD;">Annualized March Run Rate</div>
                <div style="font-size:2.3rem;font-weight:800;margin-top:.45rem;color:#F8FAFC;">{_currency(annualized_run_rate)}</div>
                <div style="margin-top:.4rem;color:#94A3B8;">Annualized from March 2026 actuals-to-date.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    row_one = st.columns(2)
    with row_one[0]:
        overview_revenue = comparison_display.copy()
        overview_revenue["revenue_actual"] = overview_revenue["revenue_display"]
        st.plotly_chart(line_bar_chart(overview_revenue, "revenue", "Revenue vs Plan"), use_container_width=True)
    with row_one[1]:
        overview_margin = comparison_display.copy()
        overview_margin["gross_margin_pct_actual"] = overview_margin["gross_margin_pct_display"]
        st.plotly_chart(margin_trend_chart(overview_margin), use_container_width=True)

    row_two = st.columns([0.95, 1.05])
    with row_two[0]:
        st.markdown('<div class="pm-panel">', unsafe_allow_html=True)
        st.markdown("#### Run-Rate Snapshot")
        st.caption("Definitions: Positive cash flow month is the first month when monthly net cash flow turns positive and stays positive after that. Safe owner draw means a recurring monthly draw that still keeps projected cash above the safety threshold for every following month.")
        st.markdown(f"Projected current month revenue: **{_currency(current_projection['projected_month_revenue'])}**")
        st.markdown(f"Projected current month profit: **{_currency(current_projection['projected_month_profit'])}**")
        st.markdown(f"Projected full-year revenue: **{_currency(year_projection['projected_year_revenue'])}**")
        st.markdown(f"Projected full-year profit: **{_currency(year_projection['projected_year_profit'])}**")
        st.markdown("---")
        st.markdown(f"First positive cash flow month: **{_month(base_flags.positive_cash_flow_month)}**")
        st.markdown(f"Capital injection month: **{_month(base_flags.first_injection_month)}**")
        st.markdown(f"Required injection: **{_currency(base_flags.required_injection)}**")
        st.markdown(f"Earliest safe owner draw month: **{_month(base_flags.safe_draw_month)}**")
        st.markdown(f"Suggested safe monthly draw: **{_currency(base_flags.suggested_draw)}**")
        st.markdown("</div>", unsafe_allow_html=True)
    with row_two[1]:
        st.plotly_chart(waterfall_chart(current_row), use_container_width=True)

with tabs[1]:
    metric_for_table = st.selectbox(
        "Variance metric",
        options=["revenue", "gross_margin_pct", "payroll", "net_operating_profit", "cash_flow"],
        index=0,
        key="variance_metric",
    )
    chart_row_1 = st.columns(2)
    with chart_row_1[0]:
        revenue_chart = comparison_display.copy()
        revenue_chart["revenue_actual"] = revenue_chart["revenue_display"]
        st.plotly_chart(line_bar_chart(revenue_chart, "revenue", "Revenue vs Plan"), use_container_width=True)
    with chart_row_1[1]:
        margin_chart_frame = comparison_display.copy()
        margin_chart_frame["gross_margin_pct_actual"] = margin_chart_frame["gross_margin_pct_display"]
        st.plotly_chart(line_bar_chart(margin_chart_frame, "gross_margin_pct", "Margin vs Plan", ".0%"), use_container_width=True)

    chart_row_2 = st.columns(2)
    with chart_row_2[0]:
        payroll_chart = comparison_display.copy()
        payroll_chart["payroll_actual"] = payroll_chart["payroll_display"]
        st.plotly_chart(line_bar_chart(payroll_chart, "payroll", "Payroll vs Plan"), use_container_width=True)
    with chart_row_2[1]:
        nop_chart = comparison_display.copy()
        nop_chart["net_operating_profit_actual"] = nop_chart["net_operating_profit_display"]
        st.plotly_chart(line_bar_chart(nop_chart, "net_operating_profit", "Operating Profit vs Plan"), use_container_width=True)

    chart_row_3 = st.columns(2)
    with chart_row_3[0]:
        cashflow_chart = comparison_display.copy()
        cashflow_chart["cash_flow_actual"] = cashflow_chart["cash_flow_display"]
        st.plotly_chart(line_bar_chart(cashflow_chart, "cash_flow", "Cash Flow vs Plan"), use_container_width=True)
    with chart_row_3[1]:
        st.plotly_chart(variance_combo(comparison, metric_for_table, "Variance to Plan"), use_container_width=True)

    st.markdown("#### Variance Table")
    variance_df = variance_table(comparison, metric_for_table)
    if "Variance %" in variance_df.columns:
        variance_df["Variance %"] = variance_df["Variance %"].map(lambda value: None if pd.isna(value) else f"{value:.1%}")
    st.dataframe(variance_df, use_container_width=True, hide_index=True)

with tabs[2]:
    st.markdown("### Scenario Engine")
    st.caption("Adjust the operational levers below. Each scenario recalculates revenue, margin, staffing, cash flow, safety threshold, capital injection, and owner draw timing.")
    st.info("Positive cash flow month = first month when monthly net cash flow turns positive and remains positive in all following months. Safe owner draw = a recurring monthly draw that still leaves projected cash above the safety threshold for all following months.")
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
            st.markdown('<div class="pm-panel">', unsafe_allow_html=True)
            st.markdown(f"#### {summary.scenario}")
            st.write(f"Monthly revenue: {_currency(summary.monthly_revenue)}")
            st.write(f"Monthly gross profit: {_currency(summary.monthly_gross_profit)}")
            st.write(f"Monthly operating profit: {_currency(summary.monthly_operating_profit)}")
            st.write(f"Monthly net cash flow: {_currency(summary.monthly_net_cash_flow)}")
            st.write(f"Ending cash balance: {_currency(summary.ending_cash_balance)}")
            st.write(f"First positive cash flow month: {_month(summary.positive_cash_flow_month)}")
            st.write(f"Cash falls below threshold: {_month(summary.threshold_breach_month)}")
            st.write(f"Capital injection needed: {_currency(summary.capital_injection_needed)}")
            st.write(f"Earliest safe owner draw month: {_month(summary.safe_distribution_month)}")
            st.write(f"Suggested safe monthly draw: {_currency(summary.suggested_monthly_distribution)}")
            if draw_warnings[summary.scenario]:
                st.warning("This owner draw level causes the business to require additional capital.")
            st.markdown("</div>", unsafe_allow_html=True)

    chart_left, chart_right = st.columns([1.1, 0.9])
    with chart_left:
        st.plotly_chart(scenario_cash_chart(scenario_frames, scenario_assumptions["Medium Case"]["cash_safety_threshold"]), use_container_width=True)
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
        st.dataframe(scenario_df, use_container_width=True, hide_index=True)

    metric_choice = st.selectbox(
        "Scenario chart metric",
        options=["revenue", "gross_profit", "net_operating_profit", "cash_flow", "cash_balance"],
        index=0,
        key="scenario_metric_choice",
    )
    scenario_metric_fig = multi_scenario_metric_chart(
        scenario_frames,
        metric_choice,
        f"Scenario Lens: {metric_choice.replace('_', ' ').title()}",
    )
    st.plotly_chart(scenario_metric_fig, use_container_width=True)

with tabs[3]:
    cash_left, cash_right = st.columns([1.25, 0.75])
    with cash_left:
        st.plotly_chart(scenario_cash_chart(scenario_frames, safety_threshold), use_container_width=True)
    with cash_right:
        st.markdown('<div class="pm-panel">', unsafe_allow_html=True)
        st.markdown("#### Cash Planning Summary")
        cash_table = pd.DataFrame(
            [
                {"Scenario": name, "Positive cash flow month": _month(flags.positive_cash_flow_month), "Injection month": _month(flags.first_injection_month), "Required injection": _currency(flags.required_injection), "Safe draw month": _month(flags.safe_draw_month), "Suggested draw": _currency(flags.suggested_draw), "Draw warning": "Owner draw triggers capital need" if draw_warnings[name] else "No draw warning"}
                for name, flags in scenario_flags.items()
            ]
        )
        st.dataframe(cash_table, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

with tabs[4]:
    op_row_1 = st.columns(2)
    with op_row_1[0]:
        st.plotly_chart(operating_metrics_chart(comparison, "sales_count_actual", "Sales Count by Month", "#7BC043"), use_container_width=True)
    with op_row_1[1]:
        st.plotly_chart(operating_metrics_chart(comparison, "purchase_count_actual", "Purchase Count by Month", "#377DFF"), use_container_width=True)

    op_row_2 = st.columns(2)
    with op_row_2[0]:
        st.plotly_chart(operating_metrics_chart(comparison, "avg_sale_value_actual", "Average Sale Value", "#F5B700"), use_container_width=True)
    with op_row_2[1]:
        st.plotly_chart(operating_metrics_chart(comparison, "avg_purchase_value_actual", "Average Purchase Value", "#8E6CEF"), use_container_width=True)

    op_row_3 = st.columns(2)
    with op_row_3[0]:
        st.plotly_chart(operating_metrics_chart(comparison, "sales_per_staff_hour_actual", "Sales per Staff Hour", "#F45B69"), use_container_width=True)
    with op_row_3[1]:
        st.plotly_chart(operating_metrics_chart(comparison, "inventory_value_actual", "Inventory Value", "#17B7A5"), use_container_width=True)
