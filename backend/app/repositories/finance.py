from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finance import BudgetCategory, Expense, ExpenseStatus
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.task import Task
from app.schemas.finance import ExpenseSort, SortOrder
from app.services.authorization import accessible_project_ids


class FinanceRepository:
    def __init__(self, session: AsyncSession, owner_user_id: UUID) -> None:
        self.session = session
        self.owner_user_id = owner_user_id

    async def get_project(self, project_id: UUID) -> Project | None:
        return (
            await self.session.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.id.in_(accessible_project_ids(self.owner_user_id)),
                )
            )
        ).scalar_one_or_none()

    async def get_category(self, project_id: UUID, category_id: UUID) -> BudgetCategory | None:
        return (
            await self.session.execute(
                select(BudgetCategory)
                .join(Project, Project.id == BudgetCategory.project_id)
                .where(
                    BudgetCategory.id == category_id,
                    BudgetCategory.project_id == project_id,
                    Project.id.in_(accessible_project_ids(self.owner_user_id)),
                )
            )
        ).scalar_one_or_none()

    async def list_categories(self, project_id: UUID) -> list[BudgetCategory]:
        result = await self.session.execute(
            select(BudgetCategory)
            .where(BudgetCategory.project_id == project_id)
            .order_by(BudgetCategory.name, BudgetCategory.id)
        )
        return list(result.scalars())

    async def category_name_exists(
        self, project_id: UUID, name: str, *, exclude_category_id: UUID | None = None
    ) -> bool:
        query = select(func.count(BudgetCategory.id)).where(
            BudgetCategory.project_id == project_id,
            func.lower(BudgetCategory.name) == name.lower(),
        )
        if exclude_category_id:
            query = query.where(BudgetCategory.id != exclude_category_id)
        return bool((await self.session.execute(query)).scalar_one())

    async def category_expense_count(self, project_id: UUID, category_id: UUID) -> int:
        return int(
            (
                await self.session.execute(
                    select(func.count(Expense.id)).where(
                        Expense.project_id == project_id,
                        Expense.budget_category_id == category_id,
                    )
                )
            ).scalar_one()
        )

    async def get_expense(self, project_id: UUID, expense_id: UUID) -> Expense | None:
        return (
            await self.session.execute(
                select(Expense)
                .join(Project, Project.id == Expense.project_id)
                .options(selectinload(Expense.category))
                .where(
                    Expense.id == expense_id,
                    Expense.project_id == project_id,
                    Project.id.in_(accessible_project_ids(self.owner_user_id)),
                )
            )
        ).scalar_one_or_none()

    async def list_expenses(
        self,
        project_id: UUID,
        *,
        search: str | None,
        status: ExpenseStatus | None,
        category_id: UUID | None,
        sort_by: ExpenseSort,
        sort_order: SortOrder,
    ) -> tuple[list[Expense], int]:
        filters = [Expense.project_id == project_id]
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Expense.description.ilike(term),
                    Expense.supplier.ilike(term),
                    Expense.payer.ilike(term),
                )
            )
        if status:
            filters.append(Expense.status == status)
        if category_id:
            filters.append(Expense.budget_category_id == category_id)
        total = int(
            (
                await self.session.execute(select(func.count(Expense.id)).where(*filters))
            ).scalar_one()
        )
        sort_column = Expense.date if sort_by == ExpenseSort.DATE else Expense.amount
        ordering = sort_column.asc() if sort_order == SortOrder.ASC else sort_column.desc()
        result = await self.session.execute(
            select(Expense)
            .options(selectinload(Expense.category))
            .where(*filters)
            .order_by(ordering, Expense.created_at.desc(), Expense.id)
        )
        return list(result.scalars()), total

    async def all_expenses(self, project_id: UUID) -> list[Expense]:
        result = await self.session.execute(
            select(Expense)
            .options(selectinload(Expense.category))
            .where(Expense.project_id == project_id)
            .order_by(Expense.date, Expense.id)
        )
        return list(result.scalars())

    async def get_task(self, project_id: UUID, task_id: UUID) -> Task | None:
        return (
            await self.session.execute(
                select(Task).where(Task.id == task_id, Task.project_id == project_id)
            )
        ).scalar_one_or_none()

    async def get_milestone(self, project_id: UUID, milestone_id: UUID) -> Milestone | None:
        return (
            await self.session.execute(
                select(Milestone).where(
                    Milestone.id == milestone_id, Milestone.project_id == project_id
                )
            )
        ).scalar_one_or_none()
