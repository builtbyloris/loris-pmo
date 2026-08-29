from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.analytics.budget import FinancialStatus
from app.models.finance import ExpenseStatus


def _required_text(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("must not be empty")
    return cleaned


class BudgetUpdate(BaseModel):
    planned_budget: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class BudgetRead(BaseModel):
    project_id: UUID
    planned_budget: Decimal
    total_category_allocation: Decimal
    unallocated_budget: Decimal
    allocation_exceeds_budget: bool


class BudgetCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    planned_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=10000)

    _strip_name = field_validator("name")(_required_text)


class BudgetCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    planned_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return _required_text(value) if value is not None else None

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> "BudgetCategoryUpdate":
        for field_name in ("name", "planned_amount"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class BudgetCategoryRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    planned_amount: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseCreate(BaseModel):
    budget_category_id: UUID | None = None
    description: str = Field(min_length=1, max_length=300)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    date: Date
    supplier: str | None = Field(default=None, max_length=200)
    payer: str | None = Field(default=None, max_length=200)
    status: ExpenseStatus = ExpenseStatus.PLANNED
    task_id: UUID | None = None
    milestone_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=10000)

    _strip_description = field_validator("description")(_required_text)


class ExpenseUpdate(BaseModel):
    budget_category_id: UUID | None = None
    description: str | None = Field(default=None, min_length=1, max_length=300)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    date: Date | None = None
    supplier: str | None = Field(default=None, max_length=200)
    payer: str | None = Field(default=None, max_length=200)
    status: ExpenseStatus | None = None
    task_id: UUID | None = None
    milestone_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        return _required_text(value) if value is not None else None

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> "ExpenseUpdate":
        for field_name in ("description", "amount", "date", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ExpenseRead(BaseModel):
    id: UUID
    project_id: UUID
    budget_category_id: UUID | None
    category_name: str | None
    description: str
    amount: Decimal
    date: Date
    supplier: str | None
    payer: str | None
    status: ExpenseStatus
    task_id: UUID | None
    milestone_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ExpenseList(BaseModel):
    items: list[ExpenseRead]
    total: int = Field(ge=0)


class ExpenseSort(StrEnum):
    DATE = "date"
    AMOUNT = "amount"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class FinancialTotals(BaseModel):
    planned_budget: Decimal
    actual_cost: Decimal
    committed_cost: Decimal
    planned_expense_cost: Decimal
    forecast: Decimal
    remaining_budget: Decimal
    actual_variance: Decimal
    budget_utilization: Decimal | None
    financial_status: FinancialStatus


class CategoryAnalytics(FinancialTotals):
    category_id: UUID
    category_name: str


class MonthlyTrend(BaseModel):
    month: str
    planned: Decimal
    committed: Decimal
    actual: Decimal


class BudgetAnalytics(BaseModel):
    totals: FinancialTotals
    categories: list[CategoryAnalytics]
    uncategorized: FinancialTotals
    monthly_trend: list[MonthlyTrend]
    total_category_allocation: Decimal
    unallocated_budget: Decimal
    allocation_exceeds_budget: bool
