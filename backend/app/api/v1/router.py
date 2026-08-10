"""L0 独占的领域 Router 聚合器。"""

from fastapi import APIRouter

from app.domains.audit.api import router as audit_router
from app.domains.auth.api import auth_router, metadata_router, users_router
from app.domains.bids.router import router as bids_router
from app.domains.evaluations.router import router as evaluations_router
from app.domains.files.api import files_router
from app.domains.health import router as health_router
from app.domains.jobs.api import jobs_router
from app.domains.notifications.api import router as notifications_router
from app.domains.portal.router import router as portal_router
from app.domains.search.api import router as search_router
from app.domains.settings.api import router as settings_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(metadata_router)
api_router.include_router(files_router)
api_router.include_router(jobs_router)
api_router.include_router(notifications_router)
api_router.include_router(settings_router)
api_router.include_router(audit_router)
api_router.include_router(search_router)
api_router.include_router(bids_router)
api_router.include_router(evaluations_router)
api_router.include_router(portal_router)
