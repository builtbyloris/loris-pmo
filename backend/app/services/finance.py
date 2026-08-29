from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.budget import BudgetNumbers, calculate_budget, monthly_trend
from app.core.errors import AppError
from app.models.finance import BudgetCategory, Expense, ExpenseStatus
from app.models.project import Project
from app.repositories.finance import FinanceRepository
from app.schemas.finance import (
    BudgetAnalytics,
    BudgetCategoryCreate,
    BudgetCategoryRead,
    BudgetCategoryUpdate,
    BudgetRead,
    BudgetUpdate,
    CategoryAnalytics,
    ExpenseCreate,
    ExpenseList,
    ExpenseRead,
    ExpenseUpdate,
    FinancialTotals,
    MonthlyTrend,
)
from app.services.audit import AuditService


class FinanceService:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id
        self.repository = FinanceRepository(session, owner_user_id)
        self.audit = AuditService(session, owner_user_id)

    async def _project_or_404(self, project_id: UUID) -> Project:
        project = await self.repository.get_project(project_id)
        if project is None:
            raise AppError(code="project_not_found", message="Project not found.", status_code=404)
        return project

    @staticmethod
    def _ensure_mutable(project: Project) -> None:
        if project.archived_at is not None:
            raise AppError(
                code="project_archived",
                message="Archived projects are read-only.",
                status_code=409,
            )

    async def _commit(self, *, category_conflict: bool = False) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            if category_conflict:
                raise AppError(
                    code="budget_category_exists",
                    message="A budget category with this name already exists.",
                    status_code=409,
                ) from exc
            raise

    async def _category_or_404(
        self, project_id: UUID, category_id: UUID
    ) -> BudgetCategory:
        category = await self.repository.get_category(project_id, category_id)
        if category is None:
            raise AppError(
                code="budget_category_not_found",
                message="Budget category not found.",
                status_code=404,
            )
        return category

    async def _expense_or_404(self, project_id: UUID, expense_id: UUID) -> Expense:
        expense = await self.repository.get_expense(project_id, expense_id)
        if expense is None:
            raise AppError(code="expense_not_found", message="Expense not found.", status_code=404)
        return expense

    async def _validate_links(
        self,
        project_id: UUID,
        *,
        category_id: UUID | None,
        task_id: UUID | None,
        milestone_id: UUID | None,
    ) -> None:
        if category_id and await self.repository.get_category(project_id, category_id) is None:
            raise AppError(
                code="invalid_expense_category",
                message="The category must belong to this project.",
                status_code=422,
            )
        if task_id and await self.repository.get_task(project_id, task_id) is None:
            raise AppError(
                code="invalid_expense_task",
                message="The task must belong to this project.",
                status_code=422,
            )
        if milestone_id and await self.repository.get_milestone(project_id, milestone_id) is None:
            raise AppError(
                code="invalid_expense_milestone",
                message="The milestone must belong to this project.",
                status_code=422,
            )

    @staticmethod
    def _expense_read(expense: Expense) -> ExpenseRead:
        return ExpenseRead(
            id=expense.id,
            project_id=expense.project_id,
            budget_category_id=expense.budget_category_id,
            category_name=expense.category.name if expense.category else None,
            description=expense.description,
            amount=expense.amount,
            date=expense.date,
            supplier=expense.supplier,
            payer=expense.payer,
            status=expense.status,
            task_id=expense.task_id,
            milestone_id=expense.milestone_id,
            notes=expense.notes,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
        )

    @staticmethod
    def _financial_totals(numbers: BudgetNumbers) -> FinancialTotals:
        return FinancialTotals(**vars(numbers))

    async def get_budget(self, project_id: UUID) -> BudgetRead:
        project = await self._project_or_404(project_id)
        categories = await self.repository.list_categories(project_id)
        allocated = sum((category.planned_amount for category in categories), Decimal("0"))
        return BudgetRead(
            project_id=project.id,
            planned_budget=project.planned_budget,
            total_category_allocation=allocated,
            unallocated_budget=project.planned_budget - allocated,
            allocation_exceeds_budget=allocated > project.planned_budget,
        )

    async def update_budget(self, project_id: UUID, data: BudgetUpdate) -> BudgetRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        before = project.planned_budget
        if before != data.planned_budget:
            project.planned_budget = data.planned_budget
            self.audit.record(
                project_id=project.id,
                action="budget.changed",
                entity_type="project_budget",
                entity_id=project.id,
                changes={"from": str(before), "to": str(data.planned_budget)},
            )
            await self._commit()
        return await self.get_budget(project_id)

    async def list_categories(self, project_id: UUID) -> list[BudgetCategoryRead]:
        await self._project_or_404(project_id)
        return [
            BudgetCategoryRead.model_validate(category)
            for category in await self.repository.list_categories(project_id)
        ]

    async def create_category(
        self, project_id: UUID, data: BudgetCategoryCreate
    ) -> BudgetCategoryRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        if await self.repository.category_name_exists(project_id, data.name):
            raise AppError(
                code="budget_category_exists",
                message="A budget category with this name already exists.",
                status_code=409,
            )
        category = BudgetCategory(project_id=project_id, **data.model_dump())
        self.session.add(category)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="budget_category.created",
            entity_type="budget_category",
            entity_id=category.id,
            changes={"name": category.name, "planned_amount": str(category.planned_amount)},
        )
        await self._commit(category_conflict=True)
        return BudgetCategoryRead.model_validate(category)

    async def update_category(
        self, project_id: UUID, category_id: UUID, data: BudgetCategoryUpdate
    ) -> BudgetCategoryRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        category = await self._category_or_404(project_id, category_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return BudgetCategoryRead.model_validate(category)
        if "name" in changes and await self.repository.category_name_exists(
            project_id, changes["name"], exclude_category_id=category_id
        ):
            raise AppError(
                code="budget_category_exists",
                message="A budget category with this name already exists.",
                status_code=409,
            )
        before = {key: str(getattr(category, key)) for key in changes}
        for key, value in changes.items():
            setattr(category, key, value)
        self.audit.record(
            project_id=project_id,
            action="budget_category.updated",
            entity_type="budget_category",
            entity_id=category.id,
            changes={"before": before, "fields": list(changes)},
        )
        await self._commit(category_conflict="name" in changes)
        return BudgetCategoryRead.model_validate(
            await self._category_or_404(project_id, category_id)
        )

    async def remove_category(self, project_id: UUID, category_id: UUID) -> None:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        category = await self._category_or_404(project_id, category_id)
        if await self.repository.category_expense_count(project_id, category_id):
            raise AppError(
                code="budget_category_in_use",
                message="A category with expense history cannot be removed.",
                status_code=409,
            )
        self.audit.record(
            project_id=project_id,
            action="budget_category.removed",
            entity_type="budget_category",
            entity_id=category.id,
            changes={"name": category.name},
        )
        await self.session.delete(category)
        await self._commit()

    async def list_expenses(self, project_id: UUID, **filters) -> ExpenseList:
        await self._project_or_404(project_id)
        expenses, total = await self.repository.list_expenses(project_id, **filters)
        return ExpenseList(items=[self._expense_read(item) for item in expenses], total=total)

    async def get_expense(self, project_id: UUID, expense_id: UUID) -> ExpenseRead:
        await self._project_or_404(project_id)
        return self._expense_read(await self._expense_or_404(project_id, expense_id))

    async def create_expense(self, project_id: UUID, data: ExpenseCreate) -> ExpenseRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        await self._validate_links(
            project_id,
            category_id=data.budget_category_id,
            task_id=data.task_id,
            milestone_id=data.milestone_id,
        )
        expense = Expense(project_id=project_id, **data.model_dump())
        self.session.add(expense)
        await self.session.flush()
        self.audit.record(
            project_id=project_id,
            action="expense.created",
            entity_type="expense",
            entity_id=expense.id,
            changes={
                "description": expense.description,
                "amount": str(expense.amount),
                "status": expense.status.value,
            },
        )
        await self._commit()
        return self._expense_read(await self._expense_or_404(project_id, expense.id))

    async def update_expense(
        self, project_id: UUID, expense_id: UUID, data: ExpenseUpdate
    ) -> ExpenseRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        expense = await self._expense_or_404(project_id, expense_id)
        if expense.status == ExpenseStatus.CANCELLED:
            raise AppError(
                code="expense_cancelled",
                message="Cancelled expenses are read-only.",
                status_code=409,
            )
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return self._expense_read(expense)
        await self._validate_links(
            project_id,
            category_id=changes.get("budget_category_id", expense.budget_category_id),
            task_id=changes.get("task_id", expense.task_id),
            milestone_id=changes.get("milestone_id", expense.milestone_id),
        )
        previous_status = expense.status
        before = {
            key: str(getattr(expense, key)) if getattr(expense, key) is not None else None
            for key in changes
        }
        for key, value in changes.items():
            setattr(expense, key, value)
        self.audit.record(
            project_id=project_id,
            action="expense.updated",
            entity_type="expense",
            entity_id=expense.id,
            changes={"before": before, "fields": list(changes)},
        )
        if expense.status != previous_status:
            self.audit.record(
                project_id=project_id,
                action="expense.status_changed",
                entity_type="expense",
                entity_id=expense.id,
                changes={"from": previous_status.value, "to": expense.status.value},
            )
            if expense.status == ExpenseStatus.CANCELLED:
                self.audit.record(
                    project_id=project_id,
                    action="expense.cancelled",
                    entity_type="expense",
                    entity_id=expense.id,
                )
        await self._commit()
        return self._expense_read(await self._expense_or_404(project_id, expense.id))

    async def cancel_expense(self, project_id: UUID, expense_id: UUID) -> ExpenseRead:
        project = await self._project_or_404(project_id)
        self._ensure_mutable(project)
        expense = await self._expense_or_404(project_id, expense_id)
        if expense.status == ExpenseStatus.CANCELLED:
            return self._expense_read(expense)
        return await self.update_expense(
            project_id, expense_id, ExpenseUpdate(status=ExpenseStatus.CANCELLED)
        )

    async def analytics(self, project_id: UUID) -> BudgetAnalytics:
        project = await self._project_or_404(project_id)
        categories = await self.repository.list_categories(project_id)
        expenses = await self.repository.all_expenses(project_id)
        allocated = sum((category.planned_amount for category in categories), Decimal("0"))
        category_analytics = []
        for category in categories:
            numbers = calculate_budget(
                category.planned_amount,
                [expense for expense in expenses if expense.budget_category_id == category.id],
            )
            category_analytics.append(
                CategoryAnalytics(
                    category_id=category.id,
                    category_name=category.name,
                    **vars(numbers),
                )
            )
        uncategorized = calculate_budget(
            Decimal("0"),
            [expense for expense in expenses if expense.budget_category_id is None],
        )
        return BudgetAnalytics(
            totals=self._financial_totals(calculate_budget(project.planned_budget, expenses)),
            categories=category_analytics,
            uncategorized=self._financial_totals(uncategorized),
            monthly_trend=[MonthlyTrend(**vars(point)) for point in monthly_trend(expenses)],
            total_category_allocation=allocated,
            unallocated_budget=project.planned_budget - allocated,
            allocation_exceeds_budget=allocated > project.planned_budget,
        )
