from fastapi import APIRouter

from app.admin.routes.auth import router as auth_router
from app.admin.routes.booths import router as booths_router
from app.admin.routes.dashboard import router as dashboard_router
from app.admin.routes.payments import router as payments_router
from app.admin.routes.speakers import router as speakers_router
from app.admin.routes.tickets import router as tickets_router
from app.admin.routes.sponsors import router as sponsors_router
from app.admin.routes.webhooks import router as webhooks_router
from app.admin.routes.statistics import router as statistics_router

router = APIRouter(
    prefix="/admin",
)

router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(speakers_router)
router.include_router(booths_router)
router.include_router(tickets_router)
router.include_router(payments_router)
router.include_router(sponsors_router)
router.include_router(webhooks_router)
router.include_router(statistics_router)