from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass
class WorkbookSectionSummary:
    assumptions_sheet: str | None = None
    revenue_sheet: str | None = None
    expenses_sheet: str | None = None
    cash_flow_sheet: str | None = None
    balance_sheet: str | None = None
    loan_sheet: str | None = None
    startup_costs_sheet: str | None = None
    inventory_cogs_sheet: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class BudgetModel:
    source_path: str
    workbook_structure: pd.DataFrame
    section_summary: WorkbookSectionSummary
    assumptions: pd.DataFrame
    startup_costs: pd.DataFrame
    monthly_budget: pd.DataFrame
    monthly_actuals: pd.DataFrame
    annual_budget: pd.DataFrame
    cash_plan: pd.DataFrame
    balance_sheet: pd.DataFrame
    inventory_cogs: pd.DataFrame
    pos_summary: pd.DataFrame


DEFAULT_PRO_FORMA = Path(__file__).resolve().parents[1] / "PayMore_Chinook_Pro_Forma_v6.xlsx"
