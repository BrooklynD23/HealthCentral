"""
API routes for HealthCentral backend.

Organized by domain:
- documents: Import, list, view documents
- observations: Lab values and verification
- assistant: RAG-powered chat
- export: Summary and data export
- profiles: Profile management
"""

from fastapi import APIRouter

from .documents import router as documents_router
from .observations import router as observations_router
from .assistant import router as assistant_router
from .export import router as export_router
from .profiles import router as profiles_router

router = APIRouter()

# Include domain routers
router.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
router.include_router(documents_router, prefix="/documents", tags=["documents"])
router.include_router(observations_router, prefix="/observations", tags=["observations"])
router.include_router(assistant_router, prefix="/assistant", tags=["assistant"])
router.include_router(export_router, prefix="/export", tags=["export"])
