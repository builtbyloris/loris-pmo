from fastapi import APIRouter

from app.api.v1 import auth, control, finance, people, portfolio, projects, work_planning

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(control.router)
api_router.include_router(finance.router)
api_router.include_router(people.people_router)
api_router.include_router(people.project_router)
api_router.include_router(portfolio.router)
api_router.include_router(projects.router)
api_router.include_router(work_planning.router)
