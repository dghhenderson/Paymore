from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass

import pandas as pd


@dataclass
class CashFlags:
    positive_cash_flow_month: pd.Timestamp | None
    first_injection_month: pd.Timestamp | None
    required_injection: float
    safe_draw_month: pd.Timestamp | None
    suggested_draw: float
    draw_causes_injection: bool = False


@dataclass
class ScenarioSummary:
    scenario: str
    monthly_revenue: float
    monthly_gross_profit: float
    monthly_operating_profit: float
    monthly_net_cash_flow: float
    ending_cash_balance: float
    positive_cash_flow_month: pd.Timestamp | None
    threshold_breach_month: pd.Timestamp | None
    capital_injection_needed: float
    safe_distribution_month: pd.Timestamp | None
    suggested_monthly_distribution: float


def align_plan(plan: pd.DataFrame) -> pd.DataFrame:
    frame = plan.copy()
    start_period = pd.Timestamp("2026-01-01")
    if frame.empty or frame["period"].min() > start_period:
        jan_row = pd.DataFrame([{"period": start_period}])
        frame = pd.concat([jan_row, frame], ignore_index=True, sort=False)
    frame = frame.sort_values("period").drop_duplicates(subset=["period"], keep="first").reset_index(drop=True)
    numeric_defaults = {
        "revenue": 0.0,
        "orders": 0.0,
        "cogs": 0.0,
        "payroll": 0.0,
        "opex": 0.0,
        "gross_profit": 0.0,
        "operating_profit": 0.0,
        "ebitda": 0.0,
        "gross_margin_pct": 0.0,
        "cash_projection": frame["cash_projection"].iloc[0] if "cash_projection" in frame.columns else 50000.0,
        "burn_rate": 0.0,
    }
    for column, default in numeric_defaults.items():
        if column not in frame.columns:
            frame[column] = default
        frame[column] = frame[column].fillna(default)
    frame["sales_count"] = frame["orders"].round()
    frame["purchase_count"] = (frame["cogs"] / 700).round()
    frame["operating_expenses"] = frame["opex"]
    frame["owner_draws"] = 0.0
    frame["loan_payments"] = 0.0
    frame["cash_flow"] = frame["operating_profit"]
    frame["net_operating_profit"] = frame["operating_profit"]
    frame["avg_sale_value"] = frame["revenue"] / frame["sales_count"].replace(0, pd.NA)
    frame["avg_purchase_value"] = frame["cogs"] / frame["purchase_count"].replace(0, pd.NA)
    frame["inventory_value"] = frame["cogs"] * 1.1
    frame["staff_hours"] = frame["payroll"] / 22.0
    frame["sales_per_staff_hour"] = frame["sales_count"] / frame["staff_hours"].replace(0, pd.NA)
    frame["month_name"] = frame["period"].dt.strftime("%b %Y")
    return frame


def build_comparison(plan: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    comp = plan.merge(actuals, on="period", how="left", suffixes=("_plan", "_actual"))
    for metric in [
        "revenue",
        "gross_margin_pct",
        "sales_count",
        "purchase_count",
        "payroll",
        "operating_expenses",
        "net_operating_profit",
        "cash_flow",
        "cash_balance",
        "owner_draws",
        "loan_payments",
        "avg_sale_value",
        "avg_purchase_value",
        "inventory_value",
        "sales_per_staff_hour",
    ]:
        actual_col = f"{metric}_actual"
        plan_col = f"{metric}_plan"
        if actual_col not in comp.columns:
            comp[actual_col] = pd.NA
        if plan_col not in comp.columns:
            comp[plan_col] = pd.NA
        comp[f"{metric}_variance"] = comp[actual_col] - comp[plan_col]
        denominator = pd.to_numeric(comp[plan_col], errors="coerce")
        denominator = denominator.where(denominator != 0, pd.NA)
        comp[f"{metric}_variance_pct"] = comp[f"{metric}_variance"] / denominator
    return comp


def _month_progress(current_date: pd.Timestamp) -> float:
    days = calendar.monthrange(current_date.year, current_date.month)[1]
    return max(min(current_date.day / days, 1.0), 1 / days)


def current_month_projection(comparison: pd.DataFrame, current_date: pd.Timestamp) -> dict[str, float]:
    current_period = current_date.to_period("M").to_timestamp()
    row = comparison.loc[comparison["period"] == current_period]
    if row.empty:
        return {"projected_month_revenue": 0.0, "projected_month_profit": 0.0}
    row = row.iloc[0]
    progress = _month_progress(current_date)
    actual_revenue = float(row.get("revenue_actual", 0.0) or 0.0)
    actual_profit = float(row.get("net_operating_profit_actual", 0.0) or 0.0)
    return {
        "projected_month_revenue": actual_revenue / progress if actual_revenue else float(row.get("revenue_plan", 0.0) or 0.0),
        "projected_month_profit": actual_profit / progress if actual_profit else float(row.get("net_operating_profit_plan", 0.0) or 0.0),
    }


def year_run_rate_projection(comparison: pd.DataFrame, current_date: pd.Timestamp) -> dict[str, float]:
    current_period = current_date.to_period("M").to_timestamp()
    projection = current_month_projection(comparison, current_date)
    actualized = comparison[comparison["period"] < current_period]
    remaining = comparison[comparison["period"] > current_period]
    actual_revenue = actualized["revenue_actual"].fillna(0).sum()
    actual_profit = actualized["net_operating_profit_actual"].fillna(0).sum()
    return {
        "projected_year_revenue": actual_revenue + projection["projected_month_revenue"] + remaining["revenue_plan"].fillna(0).sum(),
        "projected_year_profit": actual_profit + projection["projected_month_profit"] + remaining["net_operating_profit_plan"].fillna(0).sum(),
    }


def project_scenario(
    plan: pd.DataFrame,
    actuals: pd.DataFrame,
    current_date: pd.Timestamp,
    assumptions: dict[str, float],
) -> pd.DataFrame:
    frame = plan.copy()
    current_period = current_date.to_period("M").to_timestamp()
    future_mask = frame["period"] >= current_period

    frame.loc[future_mask, "revenue"] *= 1 + assumptions["revenue_change_pct"]
    frame.loc[future_mask, "gross_margin_pct"] = assumptions["gross_margin_pct"]
    frame.loc[future_mask, "sales_count"] *= 1 + assumptions["sales_change_pct"]
    frame.loc[future_mask, "purchase_count"] *= 1 + assumptions["purchase_change_pct"]
    frame.loc[future_mask, "avg_sale_value"] = assumptions["avg_sale_value"]
    frame.loc[future_mask, "avg_purchase_value"] = assumptions["avg_purchase_value"]
    frame.loc[future_mask, "revenue"] = frame.loc[future_mask, "sales_count"] * frame.loc[future_mask, "avg_sale_value"]
    frame.loc[future_mask, "cogs"] = frame.loc[future_mask, "purchase_count"] * frame.loc[future_mask, "avg_purchase_value"]
    frame.loc[future_mask, "gross_profit"] = frame.loc[future_mask, "revenue"] * frame.loc[future_mask, "gross_margin_pct"]
    frame.loc[future_mask, "payroll"] = assumptions["payroll"]
    frame.loc[future_mask, "staff_hours"] = assumptions["staff_count"] * assumptions["hours_per_staff"]
    frame.loc[future_mask, "operating_expenses"] = plan.loc[future_mask, "operating_expenses"] + assumptions["advertising_spend"]
    frame.loc[future_mask, "owner_draws"] = assumptions["owner_draws"]
    frame.loc[future_mask, "loan_payments"] = assumptions["loan_payments"]
    frame.loc[future_mask, "inventory_value"] = frame.loc[future_mask, "purchase_count"] * frame.loc[future_mask, "avg_purchase_value"] * 1.15
    frame.loc[future_mask, "sales_per_staff_hour"] = frame.loc[future_mask, "sales_count"] / frame.loc[future_mask, "staff_hours"].replace(0, pd.NA)
    frame.loc[future_mask, "net_operating_profit"] = frame.loc[future_mask, "gross_profit"] - frame.loc[future_mask, "payroll"] - frame.loc[future_mask, "operating_expenses"]
    frame.loc[future_mask, "cash_flow"] = frame.loc[future_mask, "net_operating_profit"] - frame.loc[future_mask, "owner_draws"] - frame.loc[future_mask, "loan_payments"]

    opening_cash = float(actuals["cash_balance"].dropna().iloc[-1]) if not actuals.empty else float(plan["cash_projection"].iloc[0])
    cash_projection = []
    running_cash = opening_cash
    for _, row in frame.iterrows():
        if row["period"] < current_period:
            actual_row = actuals.loc[actuals["period"] == row["period"], "cash_balance"]
            running_cash = float(actual_row.iloc[0]) if not actual_row.empty else running_cash
        else:
            running_cash += float(row["cash_flow"])
        cash_projection.append(running_cash)
    frame["cash_balance"] = cash_projection
    return frame


def evaluate_cash_flags(frame: pd.DataFrame, safety_threshold: float) -> CashFlags:
    positive_month = None
    for idx in range(len(frame)):
        tail = frame.iloc[idx:]
        if (tail["cash_flow"] > 0).all():
            positive_month = frame.iloc[idx]["period"]
            break

    shortfall = frame["cash_balance"] - safety_threshold
    below_threshold = frame.loc[shortfall < 0]
    first_injection_month = below_threshold["period"].iloc[0] if not below_threshold.empty else None
    required_injection = abs(shortfall.min()) if not below_threshold.empty else 0.0

    safe_draw_month = None
    suggested_draw = 0.0
    for idx in range(len(frame)):
        tail = frame.iloc[idx:]
        months_remaining = pd.Series(range(1, len(tail) + 1), index=tail.index, dtype="float64")
        cushion = pd.to_numeric(tail["cash_balance"], errors="coerce") - safety_threshold
        recurring_capacity = (cushion / months_remaining).min()
        if pd.notna(recurring_capacity) and recurring_capacity > 0:
            safe_draw_month = frame.iloc[idx]["period"]
            suggested_draw = float(recurring_capacity * 0.8)
            break

    return CashFlags(
        positive_cash_flow_month=positive_month,
        first_injection_month=first_injection_month,
        required_injection=required_injection,
        safe_draw_month=safe_draw_month,
        suggested_draw=suggested_draw,
    )


def summarize_scenario(name: str, frame: pd.DataFrame, safety_threshold: float) -> ScenarioSummary:
    flags = evaluate_cash_flags(frame, safety_threshold)
    future = frame[frame["period"] >= pd.Timestamp("2026-03-01")]
    monthly_revenue = float(future["revenue"].mean()) if not future.empty else 0.0
    monthly_gross_profit = float(future["gross_profit"].mean()) if not future.empty else 0.0
    monthly_operating_profit = float(future["net_operating_profit"].mean()) if not future.empty else 0.0
    monthly_net_cash_flow = float(future["cash_flow"].mean()) if not future.empty else 0.0
    return ScenarioSummary(
        scenario=name,
        monthly_revenue=monthly_revenue,
        monthly_gross_profit=monthly_gross_profit,
        monthly_operating_profit=monthly_operating_profit,
        monthly_net_cash_flow=monthly_net_cash_flow,
        ending_cash_balance=float(frame["cash_balance"].iloc[-1]) if not frame.empty else 0.0,
        positive_cash_flow_month=flags.positive_cash_flow_month,
        threshold_breach_month=flags.first_injection_month,
        capital_injection_needed=flags.required_injection,
        safe_distribution_month=flags.safe_draw_month,
        suggested_monthly_distribution=flags.suggested_draw,
    )


def scenario_summary_table(summaries: list[ScenarioSummary]) -> pd.DataFrame:
    return pd.DataFrame([asdict(summary) for summary in summaries])


def variance_table(comparison: pd.DataFrame, metric: str) -> pd.DataFrame:
    return comparison[
        ["period", f"{metric}_actual", f"{metric}_plan", f"{metric}_variance", f"{metric}_variance_pct"]
    ].rename(
        columns={
            "period": "Month",
            f"{metric}_actual": "Actual",
            f"{metric}_plan": "Projected",
            f"{metric}_variance": "Variance",
            f"{metric}_variance_pct": "Variance %",
        }
    )


def blend_actuals_to_plan(comparison: pd.DataFrame, current_date: pd.Timestamp, months_to_blend: int = 3) -> pd.DataFrame:
    frame = comparison.copy()
    current_period = current_date.to_period("M").to_timestamp()
    metrics = ["revenue", "gross_margin_pct", "payroll", "net_operating_profit", "cash_flow"]

    for metric in metrics:
        actual_col = f"{metric}_actual"
        plan_col = f"{metric}_plan"
        display_col = f"{metric}_display"
        frame[display_col] = frame[actual_col]

        current_row = frame.loc[frame["period"] == current_period]
        if current_row.empty:
            continue

        anchor = current_row.iloc[0][actual_col]
        if pd.isna(anchor):
            anchor = current_row.iloc[0][plan_col]

        future_rows = frame.index[frame["period"] > current_period].tolist()
        for step, idx in enumerate(future_rows, start=1):
            plan_value = frame.at[idx, plan_col]
            if step <= months_to_blend:
                weight = step / months_to_blend
                frame.at[idx, display_col] = anchor + ((plan_value - anchor) * weight)
            else:
                frame.at[idx, display_col] = plan_value

    return frame
