from fastapi import HTTPException, UploadFile

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.speaker_application import SpeakerApplication
from app.repositories.speaker_application_repository import (
    create_speaker_application, find_speaker_application_by_id,
)
from app.schemas.speaker_application import (
    SpeakerApplicationCreateRequest,
)
from app.db.models.application_email_verification import (
    ApplicationEmailVerification,
)
from app.mail.sender import (
    render_mail_template,
    send_html_email,
)
from app.services.email_verification_service import (
    build_email_verification_url,
    create_application_email_verification,
)
from app.storage.s3 import extract_object_key_from_public_url, delete_s3_object, upload_speaker_profile_image
from fastapi import UploadFile

def submit_speaker_application(
        db: Session,
        request: SpeakerApplicationCreateRequest,
) -> SpeakerApplication:
    try:
        application = create_speaker_application(
            db,
            name=request.name,
            company_name=request.company_name,
            email=str(request.email).lower(),
            phone=request.phone,
            social_url=request.social_url,
            presentation_content=request.presentation_content,
            privacy_agreed=request.privacy_agreed,
        )

        _, raw_token = create_application_email_verification(
            db,
            application_type=(
                ApplicationEmailVerification.TYPE_SPEAKER
            ),
            application_id=application.id,
        )

        db.commit()
        db.refresh(application)

        verification_url = build_email_verification_url(
            raw_token,
        )

        html = render_mail_template(
            "application_received.html",
            {
                "verification_url": verification_url,
            },
        )

        # send_html_email(
        #     to_email=application.email,
        #     subject="[DAKS] 연사 신청 이메일 인증",
        #     html=html,
        # )
        print(f"인증 URL: {verification_url}")

        return application

    except SQLAlchemyError:
        db.rollback()
        raise


ALLOWED_SPEAKER_STATUSES = {
    SpeakerApplication.STATUS_PENDING,
    SpeakerApplication.STATUS_APPROVED,
    SpeakerApplication.STATUS_REJECTED,
}


def get_speaker_application_or_404(
        db: Session,
        application_id: int,
) -> SpeakerApplication:
    application = find_speaker_application_by_id(
        db,
        application_id,
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="연사 신청을 찾을 수 없습니다.",
        )

    return application


def update_speaker_application_status(
        db: Session,
        *,
        application_id: int,
        status: int,
) -> SpeakerApplication:
    if status not in ALLOWED_SPEAKER_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="올바르지 않은 신청 상태입니다.",
        )

    application = get_speaker_application_or_404(
        db,
        application_id,
    )

    try:
        application.status = status

        # 반려되면 공개되지 않도록 방어
        if status == SpeakerApplication.STATUS_REJECTED:
            application.is_public = False

        db.commit()
        db.refresh(application)

        return application

    except SQLAlchemyError:
        db.rollback()
        raise


def update_speaker_public_profile(
        db: Session,
        *,
        application_id: int,
        english_name: str | None,
        public_title: str | None,
        x_url: str | None,
        youtube_url: str | None,
        facebook_url: str | None,
        display_order: int,
        is_public: bool,
) -> SpeakerApplication:
    application = get_speaker_application_or_404(
        db,
        application_id,
    )

    if (
            is_public
            and application.status
            != SpeakerApplication.STATUS_APPROVED
    ):
        raise HTTPException(
            status_code=400,
            detail="승인된 연사만 공개할 수 있습니다.",
        )

    try:
        application.english_name = english_name
        application.public_title = public_title
        application.x_url = x_url
        application.youtube_url = youtube_url
        application.facebook_url = facebook_url
        application.display_order = display_order
        application.is_public = is_public

        db.commit()
        db.refresh(application)

        return application

    except SQLAlchemyError:
        db.rollback()
        raise


async def update_speaker_profile_image(
        db: Session,
        *,
        application_id: int,
        image: UploadFile,
) -> SpeakerApplication:
    application = get_speaker_application_or_404(
        db,
        application_id,
    )

    previous_image_url = application.profile_image_url

    _, uploaded_url = await upload_speaker_profile_image(
        speaker_id=application.id,
        file=image,
    )

    try:
        application.profile_image_url = uploaded_url

        db.commit()
        db.refresh(application)

    except SQLAlchemyError:
        db.rollback()

        uploaded_object_key = extract_object_key_from_public_url(
            uploaded_url,
        )

        if uploaded_object_key:
            delete_s3_object(uploaded_object_key)

        raise

    if previous_image_url:
        previous_object_key = extract_object_key_from_public_url(
            previous_image_url,
        )

        if previous_object_key:
            delete_s3_object(previous_object_key)

    return application