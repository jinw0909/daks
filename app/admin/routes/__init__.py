from fastapi import APIRouter

from app.admin.routes.auth import router as auth_router
from app.admin.routes.booths import router as booths_router
from app.admin.routes.dashboard import router as dashboard_router
from app.admin.routes.speakers import router as speakers_router


router = APIRouter(
    prefix="/admin",
)

router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(speakers_router)
router.include_router(booths_router)