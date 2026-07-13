from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import func

from app.db.models.booth_application import BoothApplication


def create_booth_application(
        db: Session,
        *,
        company_name: str,
        email: str,
        phone: str,
        contact_name: str,
        operation_plan: str,
        privacy_agreed: bool,
) -> BoothApplication:
    application = BoothApplication(
        company_name=company_name,
        email=email,
        phone=phone,
        contact_name=contact_name,
        operation_plan=operation_plan,
        privacy_agreed=privacy_agreed,
    )

    db.add(application)
    db.flush()

    return application


def find_booth_application_by_id(
        db: Session,
        application_id: int,
) -> BoothApplication | None:
    stmt = select(BoothApplication).where(
        BoothApplication.id == application_id,
        )

    return db.scalar(stmt)



def find_booth_applications(
        db: Session,
        *,
        status: int | None = None,
        keyword: str | None = None,
        offset: int = 0,
        limit: int = 20,
) -> list[BoothApplication]:
    stmt = select(BoothApplication)

    if status is not None:
        stmt = stmt.where(
            BoothApplication.status == status,
            )

    if keyword:
        search_keyword = f"%{keyword}%"

        stmt = stmt.where(
            BoothApplication.company_name.like(search_keyword)
            | BoothApplication.contact_name.like(search_keyword)
            | BoothApplication.email.like(search_keyword)
        )

    stmt = (
        stmt
        .order_by(BoothApplication.id.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(stmt).all())


def count_booth_applications(
        db: Session,
        *,
        status: int | None = None,
        keyword: str | None = None,
) -> int:
    stmt = select(func.count(BoothApplication.id))

    if status is not None:
        stmt = stmt.where(
            BoothApplication.status == status,
            )

    if keyword:
        search_keyword = f"%{keyword}%"

        stmt = stmt.where(
            BoothApplication.company_name.like(search_keyword)
            | BoothApplication.contact_name.like(search_keyword)
            | BoothApplication.email.like(search_keyword)
        )

    return db.scalar(stmt) or 0