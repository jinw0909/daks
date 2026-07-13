import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.application_email_verification import (
    ApplicationEmailVerification,
)
from app.repositories.booth_application_repository import (
    find_booth_application_by_id,
)
from app.repositories.email_verification_repository import (
    create_email_verification,
    find_email_verification_by_token_hash,
    invalidate_previous_verifications,
)
from app.repositories.speaker_application_repository import (
    find_speaker_application_by_id,
)


EMAIL_VERIFICATION_EXPIRE_HOURS = 24


def hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_application_email_verification(
        db: Session,
        *,
        application_type: int,
        application_id: int,
) -> tuple[ApplicationEmailVerification, str]:
    now = datetime.utcnow()

    invalidate_previous_verifications(
        db,
        application_type=application_type,
        application_id=application_id,
        invalidated_at=now,
    )

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_verification_token(raw_token)

    verification = create_email_verification(
        db,
        application_type=application_type,
        application_id=application_id,
        token_hash=token_hash,
        expires_at=now + timedelta(
            hours=EMAIL_VERIFICATION_EXPIRE_HOURS,
        ),
    )

    return verification, raw_token


def build_email_verification_url(token: str) -> str:
    return (
        f"{settings.public_base_url}"
        f"/api/public/email-verifications/verify"
        f"?token={token}"
    )


def verify_application_email(
        db: Session,
        token: str,
) -> ApplicationEmailVerification:
    token_hash = hash_verification_token(token)

    verification = find_email_verification_by_token_hash(
        db,
        token_hash,
    )

    if not verification:
        raise HTTPException(
            status_code=404,
            detail="유효하지 않은 인증 링크입니다.",
        )

    if verification.invalidated_at is not None:
        raise HTTPException(
            status_code=400,
            detail="이미 만료된 인증 링크입니다.",
        )

    if verification.verified_at is not None:
        return verification

    now = datetime.utcnow()

    if verification.expires_at < now:
        raise HTTPException(
            status_code=400,
            detail="인증 링크가 만료되었습니다.",
        )

    if (
            verification.application_type
            == ApplicationEmailVerification.TYPE_SPEAKER
    ):
        application = find_speaker_application_by_id(
            db,
            verification.application_id,
        )

    elif (
            verification.application_type
            == ApplicationEmailVerification.TYPE_BOOTH
    ):
        application = find_booth_application_by_id(
            db,
            verification.application_id,
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 신청 유형입니다.",
        )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="신청 정보를 찾을 수 없습니다.",
        )

    application.email_verified = True
    verification.verified_at = now

    db.commit()
    db.refresh(verification)

    return verification