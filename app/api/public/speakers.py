from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.public_speaker import (
    PublicSpeakerDetail,
    PublicSpeakerListItem,
)
from app.services.public_speaker_service import (
    get_public_speaker_or_404,
    get_public_speakers,
)


router = APIRouter(
    prefix="/speakers",
    tags=["공개 연사"],
)


@router.get(
    "",
    response_model=list[PublicSpeakerListItem],
)
def get_speaker_list(
        db: DbSession,
):
    return get_public_speakers(db)


@router.get(
    "/{speaker_id}",
    response_model=PublicSpeakerDetail,
)
def get_speaker_detail(
        speaker_id: int,
        db: DbSession,
):
    return get_public_speaker_or_404(
        db,
        speaker_id,
    )