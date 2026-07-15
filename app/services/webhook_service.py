
import hashlib
import hmac
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.models import (
    Payment, PaymentStatusHistory,
)




KST = ZoneInfo("Asia/Seoul")

TOSS_SECRET_KEY = os.getenv("TOSS_SECRET_KEY")
def verify_signature(
        payload: dict,
        signature: str,
) -> bool:
    """
    Toss Webhook 서명 검증용.

    실제 Toss 서명 방식과 헤더명은 공식 문서를 기준으로
    운영 반영 전에 다시 확인해야 한다.
    """
    if not TOSS_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="TOSS_SECRET_KEY is not configured",
        )

    payload_str = json.dumps(
        payload,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    expected_signature = hmac.new(
        TOSS_SECRET_KEY.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        signature,
    )


def to_int_or_none(value) -> int | None:
    if value is None or value == "":
        return None

    try:
        return int(value)

    except (TypeError, ValueError):
        return None


def add_payment_history(
        db: Session,
        payment_db: Payment,
        before_status,
        after_status,
        reason: str,
        payload: dict,
        now_kst: datetime,
) -> None:
    if before_status == after_status:
        return

    db.add(
        PaymentStatusHistory(
            payment_id=payment_db.id,
            before_status=str(before_status),
            after_status=str(after_status),
            actor="TOSS_WEBHOOK",
            reason=reason,
            payload=payload,
            created_at=now_kst,
        )
    )





def apply_common_payment_fields(
    payment_db: Payment,
    paid_amount: int | None,
    toss_payment_key: str | None,
    order_id: str | None,
    raw_payload: str | None,
) -> None:
    payment_db.paid_amount = paid_amount
    payment_db.toss_payment_key = toss_payment_key
    payment_db.order_id = order_id
    payment_db.raw_payload = raw_payload


# def find_payment_by_metadata(
#         db: Session,
#         payment_id: int | None,
#         enrollment_id: int | None,
# ) -> tuple[Payment | None, bool]:
#     """
#     1순위:
#     metadata.paymentId 기준으로 Payment.id를 조회한다.

#     2순위:
#     paymentId가 없는 기존 링크라면 enrollmentId 기준으로
#     READY 상태 Payment를 조회한다.
#     """
#     payment_db = None
#     is_legacy_fallback = False

#     if payment_id:
#         payment_db = (
#             db.query(Payment)
#             .filter(
#                 Payment.id == payment_id,
#                 )
#             .first()
#         )

#         if not payment_db:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Payment not found",
#             )

#     if not payment_db and enrollment_id:
#         candidates = (
#             db.query(Payment)
#             .filter(
#                 Payment.enrollment_id == enrollment_id,
#                 Payment.status == Payment.STATUS_READY,
#                 )
#             .order_by(
#                 Payment.id.desc(),
#             )
#             .all()
#         )

#         is_legacy_fallback = True

#         if len(candidates) == 1:
#             payment_db = candidates[0]

#         elif len(candidates) > 1:
#             raise HTTPException(
#                 status_code=409,
#                 detail=(
#                     "Multiple pending payments found "
#                     "for legacy webhook"
#                 ),
#             )

#     if (
#             payment_db
#             and enrollment_id
#             and payment_db.enrollment_id != enrollment_id
#     ):
#         raise HTTPException(
#             status_code=400,
#             detail="paymentId and enrollmentId mismatch",
#         )

#     return payment_db, is_legacy_fallback


def find_payment_by_metadata(
    db: Session,
    payment_id: int | None,
    enrollment_id: int | None,
) -> tuple[Payment | None, bool]:
    """
    1순위:
    metadata.paymentId 기준으로 Payment.id 조회

    2순위:
    paymentId가 없는 기존 webhook이면
    enrollmentId 기준으로 READY 상태 Payment 조회

    반환:
        (Payment 객체 또는 None, legacy fallback 여부)
    """

    payment_db = None
    is_legacy_fallback = False

    # =====================================
    # 1. paymentId 기준 조회
    # =====================================

    if payment_id:

        payment_db = (
            db.query(Payment)
            .filter(
                Payment.id == payment_id,
            )
            .first()
        )

        # 기존:
        # raise HTTPException(404)
        #
        # 변경:
        # 조회 실패는 호출자가 처리하도록 None 반환

        if not payment_db:
            return None, False


    # =====================================
    # 2. legacy fallback
    # paymentId 없는 기존 결제 처리
    # =====================================

    if not payment_db and enrollment_id:

        candidates = (
            db.query(Payment)
            .filter(
                Payment.enrollment_id == enrollment_id,
                Payment.status == Payment.STATUS_READY,
            )
            .order_by(
                Payment.id.desc(),
            )
            .all()
        )

        is_legacy_fallback = True


        if len(candidates) == 1:

            payment_db = candidates[0]


        elif len(candidates) > 1:

            raise HTTPException(
                status_code=409,
                detail=(
                    "Multiple pending payments found "
                    "for legacy webhook"
                ),
            )


    # =====================================
    # 3. 데이터 검증
    # =====================================

    if (
        payment_db
        and enrollment_id
        and payment_db.enrollment_id != enrollment_id
    ):

        raise HTTPException(
            status_code=400,
            detail="paymentId and enrollmentId mismatch",
        )


    return payment_db, is_legacy_fallback