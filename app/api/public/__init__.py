from fastapi import APIRouter

from app.api.public.application_email_verifications import (
    router as application_email_verification_router,
)
from app.api.public.booth_applications import (
    router as booth_application_router,
)
from app.api.public.speaker_applications import (
    router as speaker_application_router,
)
from app.api.public.speakers import (
    router as speakers_router,
)


router = APIRouter(
    prefix="/api/public",
)

router.include_router(speaker_application_router)
router.include_router(booth_application_router)
router.include_router(application_email_verification_router)
router.include_router(speakers_router)