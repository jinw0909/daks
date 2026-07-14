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
from app.api.public.webhooks import (
    router as webhook_router,
)
from app.api.public.tickets import router as tickets_router

public_router = APIRouter(
    prefix="/api/public",
)

public_router.include_router(speaker_application_router)
public_router.include_router(booth_application_router)
public_router.include_router(application_email_verification_router)
public_router.include_router(speakers_router)
public_router.include_router(tickets_router)

# prefix 없는 별도 router
router = APIRouter()

router.include_router(public_router)
router.include_router(webhook_router)