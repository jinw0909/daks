from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import func

from app.db.models.speaker_application import SpeakerApplication


def create_speaker_application(
        db: Session,
        *,
        name: str,
        company_name: str,
        email: str,
        phone: str,
        social_url: str | None,
        presentation_content: str,
        privacy_agreed: bool,
) -> SpeakerApplication:
    application = SpeakerApplication(
        name=name,
        company_name=company_name,
        email=email,
        phone=phone,
        social_url=social_url,
        presentation_content=presentation_content,
        privacy_agreed=privacy_agreed,
    )

    db.add(application)
    db.flush()

    return application


def find_speaker_application_by_id(
        db: Session,
        application_id: int,
) -> SpeakerApplication | None:
    stmt = select(SpeakerApplication).where(
        SpeakerApplication.id == application_id,
        )

    return db.scalar(stmt)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.speaker_application import SpeakerApplication


def find_speaker_applications(
        db: Session,
        *,
        status: int | None = None,
        keyword: str | None = None,
        is_public: bool | None = None,
        offset: int = 0,
        limit: int = 20,
) -> list[SpeakerApplication]:
    stmt = select(SpeakerApplication)

    if status is not None:
        stmt = stmt.where(
            SpeakerApplication.status == status,
            )

    if is_public is not None:
        stmt = stmt.where(
            SpeakerApplication.is_public.is_(is_public),
        )

    if keyword:
        keyword = keyword.strip()

        if keyword:
            pattern = f"%{keyword}%"

            stmt = stmt.where(
                SpeakerApplication.name.like(pattern)
                | SpeakerApplication.company_name.like(pattern)
                | SpeakerApplication.email.like(pattern)
                | SpeakerApplication.phone.like(pattern)
                | SpeakerApplication.english_name.like(pattern)
                | SpeakerApplication.public_title.like(pattern)
            )

    stmt = (
        stmt
        .order_by(
            SpeakerApplication.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(stmt).all())

from sqlalchemy import func, select


def count_speaker_applications(
        db: Session,
        *,
        status: int | None = None,
        keyword: str | None = None,
        is_public: bool | None = None,
) -> int:
    stmt = select(
        func.count(SpeakerApplication.id),
    )

    if status is not None:
        stmt = stmt.where(
            SpeakerApplication.status == status,
            )

    if is_public is not None:
        stmt = stmt.where(
            SpeakerApplication.is_public.is_(is_public),
        )

    if keyword:
        keyword = keyword.strip()

        if keyword:
            pattern = f"%{keyword}%"

            stmt = stmt.where(
                SpeakerApplication.name.like(pattern)
                | SpeakerApplication.company_name.like(pattern)
                | SpeakerApplication.email.like(pattern)
                | SpeakerApplication.phone.like(pattern)
                | SpeakerApplication.english_name.like(pattern)
                | SpeakerApplication.public_title.like(pattern)
            )

    return db.scalar(stmt) or 0


from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.speaker_application import SpeakerApplication


def find_public_speakers(
        db: Session,
) -> list[SpeakerApplication]:
    stmt = (
        select(SpeakerApplication)
        .where(
            SpeakerApplication.status
            == SpeakerApplication.STATUS_APPROVED,
            SpeakerApplication.is_public.is_(True),
            )
        .order_by(
            SpeakerApplication.display_order.asc(),
            SpeakerApplication.id.asc(),
        )
    )

    return list(db.scalars(stmt).all())


def find_public_speaker_by_id(
        db: Session,
        speaker_id: int,
) -> SpeakerApplication | None:
    stmt = select(SpeakerApplication).where(
        SpeakerApplication.id == speaker_id,
        SpeakerApplication.status
        == SpeakerApplication.STATUS_APPROVED,
        SpeakerApplication.is_public.is_(True),
        )

    return db.scalar(stmt)