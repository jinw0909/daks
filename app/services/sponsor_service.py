from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.sponsor import Sponsor
from app.repositories.sponsor_repository import (
    find_sponsor_by_id,
    find_sponsor_by_product_key,
)
from app.services.webhook_admin_service import build_webhook_transactions, WebhookTransaction
from app.storage.s3 import extract_object_key_from_public_url, delete_s3_object, upload_sponsor_logo_image

SPONSOR_CATEGORY_LABELS = {
    Sponsor.CATEGORY_PREMIUM: "프리미엄 스폰서",
    Sponsor.CATEGORY_GENERAL: "일반 스폰서",
    Sponsor.CATEGORY_MEDIA_PARTNER: "미디어 파트너",
    Sponsor.CATEGORY_ORGANIZER: "주최",
}


VALID_SPONSOR_CATEGORIES = set(
    SPONSOR_CATEGORY_LABELS.keys()
)


def clean_optional_string(
        value: str | None,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip()

    return normalized or None


def validate_sponsor_category(
        category: int,
) -> None:
    if category not in VALID_SPONSOR_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail="올바르지 않은 스폰서 구분입니다.",
        )


def get_sponsor_or_404(
        db: Session,
        sponsor_id: int,
) -> Sponsor:
    sponsor = find_sponsor_by_id(
        db,
        sponsor_id,
    )

    if not sponsor:
        raise HTTPException(
            status_code=404,
            detail="스폰서 정보를 찾을 수 없습니다.",
        )

    return sponsor


def validate_product_key_duplicate(
        db: Session,
        *,
        toss_product_key: str | None,
        current_sponsor_id: int | None = None,
) -> None:
    if not toss_product_key:
        return

    existing = find_sponsor_by_product_key(
        db,
        toss_product_key,
    )

    if not existing:
        return

    if (
            current_sponsor_id is not None
            and existing.id == current_sponsor_id
    ):
        return

    raise HTTPException(
        status_code=409,
        detail=(
            "이미 다른 스폰서에 등록된 "
            "Toss productKey입니다."
        ),
    )


def create_sponsor(
        db: Session,
        *,
        name: str,
        category: int,
        logo_url: str | None,
        website_url: str | None,
        toss_product_key: str | None,
        toss_product_link: str | None,
        display_order: int,
        is_active: bool,
) -> Sponsor:
    normalized_name = name.strip()

    if not normalized_name:
        raise HTTPException(
            status_code=400,
            detail="스폰서명을 입력해 주세요.",
        )

    validate_sponsor_category(category)

    normalized_product_key = clean_optional_string(
        toss_product_key
    )

    validate_product_key_duplicate(
        db,
        toss_product_key=normalized_product_key,
    )

    sponsor = Sponsor(
        name=normalized_name,
        category=category,
        logo_url=clean_optional_string(
            logo_url
        ),
        website_url=clean_optional_string(
            website_url
        ),
        toss_product_key=normalized_product_key,
        toss_product_link=clean_optional_string(
            toss_product_link
        ),
        display_order=display_order,
        is_active=is_active,
    )

    db.add(sponsor)

    try:
        db.commit()
        db.refresh(sponsor)

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "이미 사용 중인 Toss productKey이거나 "
                "중복된 데이터가 있습니다."
            ),
        ) from exc

    return sponsor


def update_sponsor(
        db: Session,
        *,
        sponsor_id: int,
        name: str,
        category: int,
        # logo_url: str | None,
        website_url: str | None,
        toss_product_key: str | None,
        toss_product_link: str | None,
        display_order: int,
        is_active: bool,
) -> Sponsor:
    sponsor = get_sponsor_or_404(
        db,
        sponsor_id,
    )

    normalized_name = name.strip()

    if not normalized_name:
        raise HTTPException(
            status_code=400,
            detail="스폰서명을 입력해 주세요.",
        )

    validate_sponsor_category(category)

    normalized_product_key = clean_optional_string(
        toss_product_key
    )

    validate_product_key_duplicate(
        db,
        toss_product_key=normalized_product_key,
        current_sponsor_id=sponsor.id,
    )

    sponsor.name = normalized_name
    sponsor.category = category
    # sponsor.logo_url = clean_optional_string(
    #     logo_url
    # )
    sponsor.website_url = clean_optional_string(
        website_url
    )
    sponsor.toss_product_key = normalized_product_key
    sponsor.toss_product_link = clean_optional_string(
        toss_product_link
    )
    sponsor.display_order = display_order
    sponsor.is_active = is_active

    try:
        db.commit()
        db.refresh(sponsor)

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "이미 사용 중인 Toss productKey이거나 "
                "중복된 데이터가 있습니다."
            ),
        ) from exc

    return sponsor


async def update_sponsor_logo_image(
        db: Session,
        *,
        sponsor_id: int,
        image: UploadFile,
) -> Sponsor:
    sponsor = get_sponsor_or_404(
        db,
        sponsor_id,
    )

    previous_image_url = sponsor.logo_url

    _, uploaded_url = await upload_sponsor_logo_image(
        sponsor_id=sponsor.id,
        file=image,
    )

    try:
        sponsor.logo_url = uploaded_url

        db.commit()
        db.refresh(sponsor)

    except SQLAlchemyError:
        db.rollback()

        uploaded_object_key = (
            extract_object_key_from_public_url(
                uploaded_url,
            )
        )

        if uploaded_object_key:
            delete_s3_object(
                uploaded_object_key
            )

        raise

    if previous_image_url:
        previous_object_key = (
            extract_object_key_from_public_url(
                previous_image_url,
            )
        )

        if previous_object_key:
            delete_s3_object(
                previous_object_key
            )

    return sponsor

def toggle_sponsor_active(
        db: Session,
        *,
        sponsor_id: int,
) -> Sponsor:
    sponsor = get_sponsor_or_404(
        db,
        sponsor_id,
    )

    sponsor.is_active = not sponsor.is_active

    db.commit()
    db.refresh(sponsor)

    return sponsor



@dataclass
class SponsorPaymentSummary:
    total_count: int
    done_count: int
    done_amount: int
    canceled_count: int
    other_count: int
    latest_received_at: datetime | None
    recent_transactions: list[WebhookTransaction]


def normalize_transaction_amount(
        value,
) -> int:
    if value is None:
        return 0

    try:
        return int(value)
    except (
            TypeError,
            ValueError,
    ):
        return 0


def get_sponsor_payment_summary(
        db: Session,
        *,
        sponsor_id: int,
        recent_limit: int = 5,
) -> SponsorPaymentSummary:
    sponsor = get_sponsor_or_404(
        db,
        sponsor_id,
    )

    if not sponsor.toss_product_key:
        return SponsorPaymentSummary(
            total_count=0,
            done_count=0,
            done_amount=0,
            canceled_count=0,
            other_count=0,
            latest_received_at=None,
            recent_transactions=[],
        )

    transactions = build_webhook_transactions(
        db,
        ticket_product_key=(
            settings.toss_ticket_product_key
        ),
    )

    sponsor_transactions = [
        transaction
        for transaction in transactions
        if (
                transaction.source_type == "SPONSOR"
                and transaction.sponsor_id == sponsor.id
        )
    ]

    done_transactions = [
        transaction
        for transaction in sponsor_transactions
        if transaction.status == "DONE"
    ]

    canceled_transactions = [
        transaction
        for transaction in sponsor_transactions
        if transaction.status in {
            "CANCELED",
            "CANCELD",
        }
    ]

    other_transactions = [
        transaction
        for transaction in sponsor_transactions
        if transaction.status not in {
            "DONE",
            "CANCELED",
            "CANCELD",
        }
    ]

    done_amount = sum(
        normalize_transaction_amount(
            transaction.amount
        )
        for transaction in done_transactions
    )

    latest_received_at = (
        sponsor_transactions[0].last_received_at
        if sponsor_transactions
        else None
    )

    return SponsorPaymentSummary(
        total_count=len(
            sponsor_transactions
        ),
        done_count=len(
            done_transactions
        ),
        done_amount=done_amount,
        canceled_count=len(
            canceled_transactions
        ),
        other_count=len(
            other_transactions
        ),
        latest_received_at=(
            latest_received_at
        ),
        recent_transactions=(
            sponsor_transactions[
                :recent_limit
            ]
        ),
    )