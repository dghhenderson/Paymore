from __future__ import annotations

import pandas as pd

from paymore_dashboard.models import BudgetModel


def build_plan_vs_actual(budget: BudgetModel) -> pd.DataFrame:
    comparison = budget.monthly_budget.copy()
    if budget.pos_summary.empty:
        comparison["revenue_actual"] = pd.NA
        comparison["gross_profit_actual"] = pd.NA
        comparison["gross_margin_pct_actual"] = pd.NA
        comparison["items_sold"] = pd.NA
        comparison["avg_sale_price_actual"] = pd.NA
        return comparison

    comparison = comparison.merge(budget.pos_summary, on="period", how="left")
    comparison["revenue_variance"] = comparison["revenue_actual"] - comparison["revenue"]
    comparison["gross_profit_variance"] = comparison["gross_profit_actual"] - comparison["gross_profit"]
    comparison["gross_margin_pct_variance"] = comparison["gross_margin_pct_actual"] - comparison["gross_margin_pct"]
    comparison["cash_gap_vs_opening"] = comparison["cash_projection"] - comparison["cash_projection"].iloc[0]
    return comparison


def executive_metrics(comparison: pd.DataFrame) -> dict[str, float]:
    latest_actual = comparison.dropna(subset=["revenue_actual"])
    latest_actual_row = latest_actual.iloc[-1] if not latest_actual.empty else None
    current_row = latest_actual_row if latest_actual_row is not None else comparison.iloc[0]
    peak_burn = comparison["burn_rate"].max()
    ending_cash = comparison["cash_projection"].iloc[-1]
    current_cash = current_row["cash_projection"]
    current_burn = current_row["burn_rate"]
    runway = (current_cash / current_burn) if current_burn and current_burn > 0 else pd.NA
    return {
        "plan_revenue_year": comparison["revenue"].sum(),
        "plan_ebitda_year": comparison["ebitda"].sum(),
        "current_cash": current_cash,
        "ending_cash": ending_cash,
        "current_burn": current_burn,
        "peak_burn": peak_burn,
        "runway_months": runway,
        "latest_revenue_actual": current_row.get("revenue_actual", pd.NA),
        "latest_margin_actual": current_row.get("gross_margin_pct_actual", pd.NA),
        "latest_avg_sale": current_row.get("avg_sale_price_actual", pd.NA),
        "latest_items_sold": current_row.get("items_sold", pd.NA),
    }


def yearly_outlook(comparison: pd.DataFrame) -> pd.DataFrame:
    frame = comparison.copy()
    frame["month"] = frame["period"].dt.strftime("%b %Y")
    return frame[
        [
            "month",
            "revenue",
            "revenue_actual",
            "gross_profit",
            "gross_profit_actual",
            "ebitda",
            "burn_rate",
            "cash_projection",
        ]
    ]
