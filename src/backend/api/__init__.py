"""
API routes for HealthCentral backend.

Organized by domain:
- documents: Import, list, view documents
- observations: Lab values and verification
- interpretations: AI-powered lab result interpretations
- medications: Medication management and adherence tracking
- notifications: Medication reminder notifications
- assistant: RAG-powered chat
- export: Summary and data export
- profiles: Profile management
- model_settings: Hardware detection and model tier selection (Phase 0.3)
"""

from fastapi import APIRouter

from .documents import router as documents_router
from .observations import router as observations_router
from .interpretations import router as interpretations_router
from .medications import router as medications_router
from .notifications import router as notifications_router
from .assistant import router as assistant_router
from .export import router as export_router
from .profiles import router as profiles_router
from .model_settings import router as model_settings_router
from .memory import router as memory_router
from .gamification import router as gamification_router
from .care_tasks import router as care_tasks_router
from .timeline import router as timeline_router
from .med_reconcile import router as med_reconcile_router
from .pinboards import router as pinboards_router
from .search import router as search_router

router = APIRouter()

# Include domain routers
router.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
router.include_router(documents_router, prefix="/documents", tags=["documents"])
router.include_router(observations_router, prefix="/observations", tags=["observations"])
router.include_router(interpretations_router, prefix="/interpretations", tags=["interpretations"])
router.include_router(medications_router, prefix="/medications", tags=["medications"])
router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
router.include_router(assistant_router, prefix="/assistant", tags=["assistant"])
router.include_router(export_router, prefix="/export", tags=["export"])
router.include_router(model_settings_router, prefix="/settings/model", tags=["model-settings"])
router.include_router(memory_router, prefix="/memory", tags=["memory"])
router.include_router(gamification_router, prefix="/gamification", tags=["gamification"])
router.include_router(care_tasks_router, prefix="/care-tasks", tags=["care-tasks"])
router.include_router(timeline_router, prefix="/timeline", tags=["timeline"])
router.include_router(med_reconcile_router, prefix="/med-reconciliation", tags=["med-reconciliation"])
router.include_router(pinboards_router, prefix="/pinboards", tags=["pinboards"])
router.include_router(search_router, prefix="/search", tags=["search"])

from .feedback import router as feedback_router
router.include_router(feedback_router, prefix="/feedback", tags=["feedback"])
