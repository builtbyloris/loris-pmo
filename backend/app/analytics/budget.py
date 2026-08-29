from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.models.finance import Expense, ExpenseStatus

MONEY = Decimal("0.01")
WARNING_UTILIZATION_PERCENT = Decimal("75.00")
CRITICAL_UTILIZATION_PERCENT = Decimal("90.00")


class FinancialStatus(StrEnum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class BudgetNumbers:
    planned_budget: Decimal
    actual_cost: Decimal
    committed_cost: Decimal
    planned_expense_cost: Decimal
    forecast: Decimal
    remaining_budget: Decimal
    actual_variance: Decimal
    budget_utilization: Decimal | None
    financial_status: FinancialStatus


@dataclass(frozen=True)
class MonthlyNumbers:
    month: str
    planned: Decimal
    committed: Decimal
    actual: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def utilization(used: Decimal, budget: Decimal) -> Decimal | None:
    if budget == 0:
        return None
    return ((used / budget) * Decimal("100")).quantize(MONEY, rounding=ROUND_HALF_UP)


def financial_status(value: Decimal | None) -> FinancialStatus:
    if value is None:
        return FinancialStatus.UNAVAILABLE
    if value > CRITICAL_UTILIZATION_PERCENT:
        return FinancialStatus.CRITICAL
    if value >= WARNING_UTILIZATION_PERCENT:
        return FinancialStatus.WARNING
    return FinancialStatus.NORMAL


def calculate_budget(planned_budget: Decimal, expenses: list[Expense]) -> BudgetNumbers:
    actual = sum(
        (expense.amount for expense in expenses if expense.status == ExpenseStatus.PAID),
        Decimal("0"),
    )
    committed = sum(
        (expense.amount for expense in expenses if expense.status == ExpenseStatus.PENDING),
        Decimal("0"),
    )
    planned_expenses = sum(
        (expense.amount for expense in expenses if expense.status == ExpenseStatus.PLANNED),
        Decimal("0"),
    )
    used = actual + committed
    utilization_value = utilization(used, planned_budget)
    return BudgetNumbers(
        planned_budget=_money(planned_budget),
        actual_cost=_money(actual),
        committed_cost=_money(committed),
        planned_expense_cost=_money(planned_expenses),
        forecast=_money(actual + committed + planned_expenses),
        remaining_budget=_money(planned_budget - used),
        actual_variance=_money(planned_budget - actual),
        budget_utilization=utilization_value,
        financial_status=financial_status(utilization_value),
    )


def monthly_trend(expenses: list[Expense]) -> list[MonthlyNumbers]:
    grouped: dict[str, dict[ExpenseStatus, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: Decimal("0"))
    )
    for expense in expenses:
        if expense.status == ExpenseStatus.CANCELLED:
            continue
        grouped[expense.date.strftime("%Y-%m")][expense.status] += expense.amount
    return [
        MonthlyNumbers(
            month=month,
            planned=_money(values[ExpenseStatus.PLANNED]),
            committed=_money(values[ExpenseStatus.PENDING]),
            actual=_money(values[ExpenseStatus.PAID]),
        )
        for month, values in sorted(grouped.items())
    ]
