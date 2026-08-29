from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_csrf
from app.core.database import get_db
from app.models.finance import ExpenseStatus
from app.schemas.finance import (
    BudgetAnalytics,
    BudgetCategoryCreate,
    BudgetCategoryRead,
    BudgetCategoryUpdate,
    BudgetRead,
    BudgetUpdate,
    ExpenseCreate,
    ExpenseList,
    ExpenseRead,
    ExpenseSort,
    ExpenseUpdate,
    SortOrder,
)
from app.services.finance import FinanceService

router = APIRouter(prefix="/projects/{project_id}", tags=["finance"])
Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("/budget", response_model=BudgetRead)
async def get_budget(project_id: UUID, user: CurrentUser, session: Session) -> BudgetRead:
    return await FinanceService(session, user.id).get_budget(project_id)


@router.patch("/budget", response_model=BudgetRead, dependencies=[Depends(require_csrf)])
async def update_budget(
    project_id: UUID, data: BudgetUpdate, user: CurrentUser, session: Session
) -> BudgetRead:
    return await FinanceService(session, user.id).update_budget(project_id, data)


@router.get("/budget/categories", response_model=list[BudgetCategoryRead])
async def list_categories(
    project_id: UUID, user: CurrentUser, session: Session
) -> list[BudgetCategoryRead]:
    return await FinanceService(session, user.id).list_categories(project_id)


@router.post(
    "/budget/categories",
    response_model=BudgetCategoryRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_category(
    project_id: UUID,
    data: BudgetCategoryCreate,
    user: CurrentUser,
    session: Session,
) -> BudgetCategoryRead:
    return await FinanceService(session, user.id).create_category(project_id, data)


@router.patch(
    "/budget/categories/{category_id}",
    response_model=BudgetCategoryRead,
    dependencies=[Depends(require_csrf)],
)
async def update_category(
    project_id: UUID,
    category_id: UUID,
    data: BudgetCategoryUpdate,
    user: CurrentUser,
    session: Session,
) -> BudgetCategoryRead:
    return await FinanceService(session, user.id).update_category(project_id, category_id, data)


@router.delete(
    "/budget/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def remove_category(
    project_id: UUID, category_id: UUID, user: CurrentUser, session: Session
) -> None:
    await FinanceService(session, user.id).remove_category(project_id, category_id)


@router.get("/expenses", response_model=ExpenseList)
async def list_expenses(
    project_id: UUID,
    user: CurrentUser,
    session: Session,
    search: Annotated[str | None, Query(max_length=300)] = None,
    expense_status: Annotated[ExpenseStatus | None, Query(alias="status")] = None,
    category_id: UUID | None = None,
    sort_by: ExpenseSort = ExpenseSort.DATE,
    sort_order: SortOrder = SortOrder.DESC,
) -> ExpenseList:
    return await FinanceService(session, user.id).list_expenses(
        project_id,
        search=search,
        status=expense_status,
        category_id=category_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "/expenses",
    response_model=ExpenseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_expense(
    project_id: UUID, data: ExpenseCreate, user: CurrentUser, session: Session
) -> ExpenseRead:
    return await FinanceService(session, user.id).create_expense(project_id, data)


@router.get("/expenses/{expense_id}", response_model=ExpenseRead)
async def get_expense(
    project_id: UUID, expense_id: UUID, user: CurrentUser, session: Session
) -> ExpenseRead:
    return await FinanceService(session, user.id).get_expense(project_id, expense_id)


@router.patch(
    "/expenses/{expense_id}",
    response_model=ExpenseRead,
    dependencies=[Depends(require_csrf)],
)
async def update_expense(
    project_id: UUID,
    expense_id: UUID,
    data: ExpenseUpdate,
    user: CurrentUser,
    session: Session,
) -> ExpenseRead:
    return await FinanceService(session, user.id).update_expense(project_id, expense_id, data)


@router.post(
    "/expenses/{expense_id}/cancel",
    response_model=ExpenseRead,
    dependencies=[Depends(require_csrf)],
)
async def cancel_expense(
    project_id: UUID, expense_id: UUID, user: CurrentUser, session: Session
) -> ExpenseRead:
    return await FinanceService(session, user.id).cancel_expense(project_id, expense_id)


@router.get("/budget/analytics", response_model=BudgetAnalytics)
async def budget_analytics(
    project_id: UUID, user: CurrentUser, session: Session
) -> BudgetAnalytics:
    return await FinanceService(session, user.id).analytics(project_id)
