from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    "month",
    "revenue",
    "gross_margin_percent",
    "sales_count",
    "purchase_count",
    "payroll",
    "operating_expenses",
    "loan_payment",
    "owner_draws",
    "cash_balance",
    "average_sale_value",
    "average_purchase_value",
]

OPTIONAL_COLUMNS = ["inventory_value", "staff_hours"]

CANONICAL_ORDER = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

COLUMN_ALIASES = {
    "period": "month",
    "gross_margin_pct": "gross_margin_percent",
    "loan_payments": "loan_payment",
    "avg_sale_value": "average_sale_value",
    "avg_purchase_value": "average_purchase_value",
}


def _fallback_actuals_template() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "month": "2026-01-01",
                "revenue": 268.97,
                "gross_margin_percent": 0.6626,
                "sales_count": 3,
                "purchase_count": 8,
                "payroll": 4200.0,
                "operating_expenses": 7800.0,
                "loan_payment": 0.0,
                "owner_draws": 0.0,
                "cash_balance": 46350.0,
                "average_sale_value": 89.66,
                "average_purchase_value": 1875.0,
                "inventory_value": 15000.0,
                "staff_hours": 160.0,
            },
            {
                "month": "2026-02-01",
                "revenue": 11058.68,
                "gross_margin_percent": 0.4135,
                "sales_count": 43,
                "purchase_count": 61,
                "payroll": 9100.0,
                "operating_expenses": 12800.0,
                "loan_payment": 0.0,
                "owner_draws": 0.0,
                "cash_balance": 37100.0,
                "average_sale_value": 257.18,
                "average_purchase_value": 659.84,
                "inventory_value": 40250.0,
                "staff_hours": 290.0,
            },
            {
                "month": "2026-03-01",
                "revenue": 8689.88,
                "gross_margin_percent": 0.4216,
                "sales_count": 35,
                "purchase_count": 54,
                "payroll": 6400.0,
                "operating_expenses": 8900.0,
                "loan_payment": 0.0,
                "owner_draws": 0.0,
                "cash_balance": 33150.0,
                "average_sale_value": 248.28,
                "average_purchase_value": 811.11,
                "inventory_value": 43800.0,
                "staff_hours": 215.0,
            },
        ]
    )


def actuals_template(base_actuals: pd.DataFrame | None = None) -> pd.DataFrame:
    if base_actuals is None or base_actuals.empty:
        return _fallback_actuals_template()

    actuals = base_actuals.copy()
    if "month" not in actuals.columns and "period" not in actuals.columns:
        return _fallback_actuals_template()
    if "period" not in actuals.columns:
        actuals = normalize_actuals(actuals)

    editable = actuals.rename(
        columns={
            "period": "month",
            "gross_margin_pct": "gross_margin_percent",
            "loan_payments": "loan_payment",
            "avg_sale_value": "average_sale_value",
            "avg_purchase_value": "average_purchase_value",
        }
    ).copy()
    editable["month"] = pd.to_datetime(editable["month"]).dt.strftime("%Y-%m-%d")
    for column in CANONICAL_ORDER:
        if column not in editable.columns:
            editable[column] = 0.0
        elif column != "month":
            editable[column] = pd.to_numeric(editable[column], errors="coerce").fillna(0.0)
    return editable[CANONICAL_ORDER]


def sample_actuals(base_actuals: pd.DataFrame | None = None) -> pd.DataFrame:
    if base_actuals is not None and not base_actuals.empty:
        return base_actuals.sort_values("period").reset_index(drop=True)
    return normalize_actuals(_fallback_actuals_template())


def _monthly_sales_from_report(frame: pd.DataFrame) -> pd.DataFrame:
    sales = frame.copy()
    sales.columns = [str(col).strip() for col in sales.columns]
    required = {"Sold Price", "Gross Profit", "Sold on"}
    if not required.issubset(set(sales.columns)):
        raise ValueError("This PayMore sales report is missing one of: `Sold Price`, `Gross Profit`, `Sold on`.")
    sales["Sold on"] = pd.to_datetime(sales["Sold on"], errors="coerce")
    sales = sales.dropna(subset=["Sold on"]).copy()
    sales["month"] = sales["Sold on"].dt.to_period("M").dt.to_timestamp()
    sales["Sold Price"] = pd.to_numeric(sales["Sold Price"], errors="coerce").fillna(0.0)
    sales["Gross Profit"] = pd.to_numeric(sales["Gross Profit"], errors="coerce").fillna(0.0)
    monthly = (
        sales.groupby("month", as_index=False)
        .agg(
            revenue=("Sold Price", "sum"),
            gross_profit=("Gross Profit", "sum"),
            sales_count=("Sold Price", "size"),
        )
    )
    monthly["gross_margin_percent"] = monthly["gross_profit"] / monthly["revenue"].replace(0, pd.NA)
    monthly["average_sale_value"] = monthly["revenue"] / monthly["sales_count"].replace(0, pd.NA)
    return monthly


def parse_paymore_sales_report(upload, base_actuals: pd.DataFrame | None = None) -> pd.DataFrame:
    suffix = Path(upload.name).suffix.lower()
    raw = upload.getvalue()
    if suffix == ".csv":
        frame = pd.read_csv(BytesIO(raw), header=2)
    else:
        frame = pd.read_excel(BytesIO(raw), header=2)
    monthly = _monthly_sales_from_report(frame)
    base = actuals_template(base_actuals).copy()
    base["month"] = pd.to_datetime(base["month"]).dt.to_period("M").dt.to_timestamp()
    merged = base.merge(
        monthly[["month", "revenue", "gross_margin_percent", "sales_count", "average_sale_value"]],
        on="month",
        how="outer",
        suffixes=("_base", ""),
    ).sort_values("month")
    for metric in ["revenue", "gross_margin_percent", "sales_count", "average_sale_value"]:
        merged[metric] = merged[metric].fillna(merged.get(f"{metric}_base"))
    drop_cols = [col for col in merged.columns if col.endswith("_base")]
    if drop_cols:
        merged = merged.drop(columns=drop_cols)
    merged["purchase_count"] = merged["purchase_count"].fillna(0.0)
    merged["average_purchase_value"] = merged["average_purchase_value"].fillna(0.0)
    merged["inventory_value"] = merged["inventory_value"].fillna(0.0)
    merged["staff_hours"] = merged["staff_hours"].fillna(0.0)
    merged["loan_payment"] = merged["loan_payment"].fillna(0.0)
    merged["owner_draws"] = merged["owner_draws"].fillna(0.0)
    merged["payroll"] = merged["payroll"].fillna(0.0)
    merged["operating_expenses"] = merged["operating_expenses"].fillna(0.0)
    merged["cash_balance"] = merged["cash_balance"].fillna(0.0)
    return normalize_actuals(merged[CANONICAL_ORDER])


def validate_actuals_columns(frame: pd.DataFrame) -> list[str]:
    columns = [COLUMN_ALIASES.get(str(col).strip().lower(), str(col).strip().lower()) for col in frame.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    messages = []
    if missing:
        messages.append(
            "Missing required columns: " + ", ".join(f"`{column}`" for column in missing) + "."
        )
    return messages


def _apply_aliases(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.copy()
    renamed.columns = [COLUMN_ALIASES.get(str(col).strip().lower(), str(col).strip().lower()) for col in renamed.columns]
    return renamed


def normalize_actuals(frame: pd.DataFrame) -> pd.DataFrame:
    actuals = _apply_aliases(frame)
    messages = validate_actuals_columns(actuals)
    if messages:
        raise ValueError(" ".join(messages))

    actuals["month"] = pd.to_datetime(actuals["month"], errors="coerce")
    if actuals["month"].isna().any():
        raise ValueError("`month` must be a valid date column, for example `2026-03-01`.")
    actuals["month"] = actuals["month"].dt.to_period("M").dt.to_timestamp()

    for column in CANONICAL_ORDER:
        if column not in actuals.columns:
            actuals[column] = 0.0
        if column != "month":
            actuals[column] = pd.to_numeric(actuals[column], errors="coerce")

    invalid_numeric = []
    for column in REQUIRED_COLUMNS:
        if column == "month":
            continue
        if actuals[column].isna().any():
            invalid_numeric.append(column)
    if invalid_numeric:
        raise ValueError(
            "These columns contain invalid or blank numeric values: "
            + ", ".join(f"`{column}`" for column in invalid_numeric)
            + "."
        )

    for column in OPTIONAL_COLUMNS:
        actuals[column] = actuals[column].fillna(0.0)

    actuals = actuals[CANONICAL_ORDER].sort_values("month").reset_index(drop=True)
    actuals = actuals.rename(
        columns={
            "month": "period",
            "gross_margin_percent": "gross_margin_pct",
            "loan_payment": "loan_payments",
            "average_sale_value": "avg_sale_value",
            "average_purchase_value": "avg_purchase_value",
        }
    )
    actuals["gross_profit"] = actuals["revenue"] * actuals["gross_margin_pct"]
    actuals["sales_per_staff_hour"] = actuals["sales_count"] / actuals["staff_hours"].replace(0, pd.NA)
    actuals["net_operating_profit"] = actuals["gross_profit"] - actuals["payroll"] - actuals["operating_expenses"]
    actuals["cash_flow"] = actuals["net_operating_profit"] - actuals["owner_draws"] - actuals["loan_payments"]
    return actuals


def load_actuals_upload(upload, base_actuals: pd.DataFrame | None = None) -> pd.DataFrame:
    if upload is None:
        return sample_actuals(base_actuals)
    suffix = Path(upload.name).suffix.lower()
    raw = upload.getvalue()
    if "sold_items_report" in upload.name.lower():
        return parse_paymore_sales_report(upload, base_actuals)
    if suffix == ".csv":
        frame = pd.read_csv(BytesIO(raw))
    else:
        frame = pd.read_excel(BytesIO(raw))
    aliased = _apply_aliases(frame)
    if "sold on" in [str(col).strip().lower() for col in frame.columns]:
        monthly = _monthly_sales_from_report(frame)
        template = actuals_template(base_actuals)
        template["month"] = pd.to_datetime(template["month"]).dt.to_period("M").dt.to_timestamp()
        merged = template.merge(
            monthly[["month", "revenue", "gross_margin_percent", "sales_count", "average_sale_value"]],
            on="month",
            how="outer",
            suffixes=("_base", ""),
        ).sort_values("month")
        for metric in ["revenue", "gross_margin_percent", "sales_count", "average_sale_value"]:
            merged[metric] = merged[metric].fillna(merged.get(f"{metric}_base"))
        drop_cols = [col for col in merged.columns if col.endswith("_base")]
        if drop_cols:
            merged = merged.drop(columns=drop_cols)
        return normalize_actuals(merged[CANONICAL_ORDER])
    return normalize_actuals(aliased)
