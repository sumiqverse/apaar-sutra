"""Version 1 API router assembly."""

from fastapi import APIRouter

from app.api.routers.v1.auth import router as auth_router
from app.api.routers.v1.students import router as students_router
from app.api.routers.v1.verifications import router as verifications_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(students_router)
api_v1_router.include_router(verifications_router)

__all__ = ["api_v1_router"]
