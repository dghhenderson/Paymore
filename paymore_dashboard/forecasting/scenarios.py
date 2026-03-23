from __future__ import annotations

import pandas as pd


SCENARIO_PRESETS = {
    "Best Case": {
        "sales_growth": 0.12,
        "gross_margin_delta": 0.03,
        "payroll_delta": -0.02,
        "rent_delta": 0.0,
        "overhead_delta": -0.03,
        "purchases_delta": -0.02,
    },
    "Base Case": {
        "sales_growth": 0.0,
        "gross_margin_delta": 0.0,
        "payroll_delta": 0.0,
        "rent_delta": 0.0,
        "overhead_delta": 0.0,
        "purchases_delta": 0.0,
    },
    "Worst Case": {
        "sales_growth": -0.1,
        "gross_margin_delta": -0.03,
        "payroll_delta": 0.05,
        "rent_delta": 0.0,
        "overhead_delta": 0.06,
        "purchases_delta": 0.08,
    },
}


def apply_scenario(monthly_budget: pd.DataFrame, assumptions: dict[str, float]) -> pd.DataFrame:
    frame = monthly_budget.copy()
    frame["revenue"] = frame["revenue"] * (1 + assumptions["sales_growth"])
    frame["payroll"] = frame["payroll"] * (1 + assumptions["payroll_delta"])
    frame["rent_cam"] = frame["rent_cam"] * (1 + assumptions["rent_delta"])
    frame["cogs"] = frame["cogs"] * (1 + assumptions["purchases_delta"])

    overhead_columns = [
        "management_fees",
        "marketing_fund",
        "technology_fee",
        "google_ad_words",
        "professional_fees",
        "office_general",
        "selling_platforms",
        "music",
        "insurance",
        "license_taxes",
        "telephone_internet_cameras",
        "security",
        "utilities",
    ]
    for column in overhead_columns:
        frame[column] = frame[column] * (1 + assumptions["overhead_delta"])

    target_margin = (frame["gross_margin_pct"].fillna(0) + assumptions["gross_margin_delta"]).clip(lower=0.05, upper=0.95)
    target_gross_profit = frame["revenue"] * target_margin
    variable_other = frame["shipping_costs"] + frame["marketplace_fees"] + frame["payroll"]
    frame["cogs"] = (frame["revenue"] - target_gross_profit - variable_other).clip(lower=0)

    frame["gross_profit"] = frame["revenue"] - frame["cogs"] - frame["shipping_costs"] - frame["marketplace_fees"] - frame["payroll"]
    frame["opex"] = frame[overhead_columns + ["rent_cam"]].sum(axis=1)
    frame["operating_profit"] = frame["gross_profit"] - frame["opex"]
    frame["ebitda"] = frame["operating_profit"]
    opening_cash = float(monthly_budget["cash_projection"].iloc[0] - monthly_budget["operating_profit"].iloc[0])
    frame["cash_projection"] = opening_cash + frame["operating_profit"].cumsum()
    frame["burn_rate"] = frame["operating_profit"].apply(lambda value: abs(value) if value < 0 else 0.0)
    return frame


def scenario_summary(frame: pd.DataFrame) -> dict[str, float]:
    return {
        "Revenue": frame["revenue"].sum(),
        "EBITDA": frame["ebitda"].sum(),
        "Year-End Cash": frame["cash_projection"].iloc[-1],
        "Peak Burn": frame["burn_rate"].max(),
    }
