from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models.application_email_verification import (
    ApplicationEmailVerification,
)


def create_email_verification(
        db: Session,
        *,
        application_type: int,
        application_id: int,
        token_hash: str,
        expires_at: datetime,
) -> ApplicationEmailVerification:
    verification = ApplicationEmailVerification(
        application_type=application_type,
        application_id=application_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    db.add(verification)
    db.flush()

    return verification


def find_email_verification_by_token_hash(
        db: Session,
        token_hash: str,
) -> ApplicationEmailVerification | None:
    stmt = select(ApplicationEmailVerification).where(
        ApplicationEmailVerification.token_hash == token_hash,
        )

    return db.scalar(stmt)

def invalidate_previous_verifications(
        db: Session,
        *,
        application_type: int,
        application_id: int,
        invalidated_at: datetime,
) -> None:
    stmt = (
        update(ApplicationEmailVerification)
        .where(
            ApplicationEmailVerification.application_type
            == application_type,
            ApplicationEmailVerification.application_id
            == application_id,
            ApplicationEmailVerification.verified_at.is_(None),
            ApplicationEmailVerification.invalidated_at.is_(None),
            )
        .values(invalidated_at=invalidated_at)
    )

    db.execute(stmt)