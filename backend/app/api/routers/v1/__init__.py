"""Version 1 API router assembly."""

from fastapi import APIRouter

from app.api.routers.v1.auth import router as auth_router
from app.api.routers.v1.audit import router as audit_router
from app.api.routers.v1.students import router as students_router
from app.api.routers.v1.verifications import router as verifications_router
from app.api.routers.v1.batches import router as batches_router
from app.api.routers.v1.programs import router as programs_router
from app.api.routers.v1.integration import router as integration_router
from app.api.routers.v1.validation import router as validation_router
from app.api.routers.v1.ml import router as ml_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(students_router)
api_v1_router.include_router(verifications_router)
api_v1_router.include_router(batches_router)
api_v1_router.include_router(programs_router)
api_v1_router.include_router(integration_router)
api_v1_router.include_router(validation_router)
api_v1_router.include_router(ml_router)

__all__ = ["api_v1_router"]
