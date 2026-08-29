from fastapi import APIRouter

from app.api.v1 import auth, people, portfolio, projects, work_planning

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(people.people_router)
api_router.include_router(people.project_router)
api_router.include_router(portfolio.router)
api_router.include_router(projects.router)
api_router.include_router(work_planning.router)
