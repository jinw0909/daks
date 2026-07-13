from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.speaker_application import SpeakerApplication
from app.repositories.speaker_application_repository import (
    find_public_speaker_by_id,
    find_public_speakers,
)


def get_public_speakers(
        db: Session,
) -> list[SpeakerApplication]:
    return find_public_speakers(db)


def get_public_speaker_or_404(
        db: Session,
        speaker_id: int,
) -> SpeakerApplication:
    speaker = find_public_speaker_by_id(
        db,
        speaker_id,
    )

    if not speaker:
        raise HTTPException(
            status_code=404,
            detail="공개된 연사를 찾을 수 없습니다.",
        )

    return speaker