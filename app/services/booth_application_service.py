from http.client import HTTPException

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.application_email_verification import (
    ApplicationEmailVerification,
)
from app.db.models.booth_application import BoothApplication
from app.repositories.booth_application_repository import (
    create_booth_application, find_booth_application_by_id,
)
from app.schemas.booth_application import (
    BoothApplicationCreateRequest,
)
from app.services.email_verification_service import (
    build_email_verification_url,
    create_application_email_verification,
)


def submit_booth_application(
        db: Session,
        request: BoothApplicationCreateRequest,
) -> BoothApplication:
    try:
        application = create_booth_application(
            db,
            company_name=request.company_name,
            email=str(request.email).lower(),
            phone=request.phone,
            contact_name=request.contact_name,
            operation_plan=request.operation_plan,
            privacy_agreed=request.privacy_agreed,
        )

        _, raw_token = create_application_email_verification(
            db,
            application_type=ApplicationEmailVerification.TYPE_BOOTH,
            application_id=application.id,
        )

        db.commit()
        db.refresh(application)

    except SQLAlchemyError:
        db.rollback()
        raise

    verification_url = build_email_verification_url(raw_token)

    # SMTP 연결 전 임시 확인용
    print(f"부스 신청 인증 URL: {verification_url}")

    return application



ALLOWED_BOOTH_STATUSES = {
    BoothApplication.STATUS_PENDING,
    BoothApplication.STATUS_APPROVED,
    BoothApplication.STATUS_REJECTED,
}


def get_booth_application_or_404(
        db: Session,
        application_id: int,
) -> BoothApplication:
    application = find_booth_application_by_id(
        db,
        application_id,
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="부스 신청을 찾을 수 없습니다.",
        )

    return application


def update_booth_application_status(
        db: Session,
        *,
        application_id: int,
        status: int,
) -> BoothApplication:
    if status not in ALLOWED_BOOTH_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="올바르지 않은 신청 상태입니다.",
        )

    application = get_booth_application_or_404(
        db,
        application_id,
    )

    try:
        application.status = status

        db.commit()
        db.refresh(application)

        return application

    except SQLAlchemyError:
        db.rollback()
        raise