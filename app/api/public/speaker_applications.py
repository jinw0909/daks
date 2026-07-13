from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.schemas.speaker_application import (
    SpeakerApplicationCreateRequest,
    SpeakerApplicationCreateResponse,
)
from app.services.speaker_application_service import (
    submit_speaker_application,
)


router = APIRouter(
    prefix="/speaker-applications",
    tags=["연사 신청"],
)


@router.post(
    "",
    response_model=SpeakerApplicationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_speaker_application(
        request: SpeakerApplicationCreateRequest,
        db: DbSession,
):
    return submit_speaker_application(
        db,
        request,
    )