from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Payment
from app.repositories.payment_repository import create_ready_payment, find_payments_by_ticket_user_ids, \
    find_payment_by_id_and_ticket_user_id
from app.repositories.ticket_user_repository import create_ticket_user, find_ticket_users_by_name_and_phone, find_ticket_user_by_id_for_admin
from app.schemas.ticket import (
    TicketPaymentPrepareRequest,
    TicketPaymentPrepareResponse, TicketPaymentHistoryResponse, TicketPaymentHistoryItem, TicketPaymentHistoryRequest,
    TicketPaymentStatusResponse,
)


def build_toss_linkpay_url(
        *,
        base_url: str,
        ticket_user_id: int,
        payment_id: int,
) -> str:
    """
    기존 링크에 query string이 있어도 유지하면서
    ticketUserId와 paymentId를 추가한다.
    """

    split_url = urlsplit(base_url)

    query_params = dict(
        parse_qsl(
            split_url.query,
            keep_blank_values=True,
        )
    )

    query_params.update(
        {
            "ticketUserId": str(ticket_user_id),
            "paymentId": str(payment_id),
        }
    )

    return urlunsplit(
        (
            split_url.scheme,
            split_url.netloc,
            split_url.path,
            urlencode(query_params),
            split_url.fragment,
        )
    )


def prepare_ticket_payment(
        db: Session,
        request: TicketPaymentPrepareRequest,
) -> TicketPaymentPrepareResponse:
    try:
        ticket_user = create_ticket_user(
            db,
            name=request.name,
            phone=request.phone,
            country=request.country,
            activity_type=request.activity_type,
            registration_path=request.registration_path,
            privacy_agreed=request.privacy_agreed,
        )

        payment = create_ready_payment(
            db,
            ticket_user_id=ticket_user.id,
            payment_name=settings.ticket_payment_name,
            expected_amount=settings.ticket_expected_amount,
            toss_product_key=settings.toss_ticket_product_key,
        )

        redirect_url = build_toss_linkpay_url(
            base_url=settings.toss_ticket_product_link,
            ticket_user_id=ticket_user.id,
            payment_id=payment.id,
        )

        db.commit()

        return TicketPaymentPrepareResponse(
            ticket_user_id=ticket_user.id,
            payment_id=payment.id,
            redirect_url=redirect_url,
        )

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="결제 준비 정보를 저장하는 중 오류가 발생했습니다.",
        )

    except Exception:
        db.rollback()
        raise

def get_payment_status_name(status: int) -> str:
    status_names = {
        Payment.STATUS_READY: "결제 대기",
        Payment.STATUS_PAID: "결제 완료",
        Payment.STATUS_FAILED: "결제 실패",
        Payment.STATUS_CANCELED: "결제 취소",
    }

    return status_names.get(
        status,
        "상태 확인 필요",
    )


def mask_phone(phone: str) -> str:
    normalized = "".join(
        character
        for character in phone
        if character.isdigit()
    )

    if len(normalized) == 11:
        return (
            f"{normalized[:3]}-"
            f"****-"
            f"{normalized[-4:]}"
        )

    if len(normalized) == 10:
        return (
            f"{normalized[:3]}-"
            f"***-"
            f"{normalized[-4:]}"
        )

    return "****"


def get_ticket_payment_history(
        db: Session,
        request: TicketPaymentHistoryRequest,
) -> TicketPaymentHistoryResponse:
    ticket_users = find_ticket_users_by_name_and_phone(
        db,
        name=request.name,
        phone=request.phone,
    )

    if not ticket_users:
        raise HTTPException(
            status_code=404,
            detail="입력한 정보와 일치하는 구매 내역을 찾을 수 없습니다.",
        )

    ticket_user_ids = [
        ticket_user.id
        for ticket_user in ticket_users
    ]

    payments = find_payments_by_ticket_user_ids(
        db,
        ticket_user_ids=ticket_user_ids,
    )

    # 구매 내역 조회 화면에는 READY를 굳이 보여주지 않는 편이 자연스럽다.
    visible_payments = [
        payment
        for payment in payments
        if payment.status != Payment.STATUS_READY
    ]

    if not visible_payments:
        raise HTTPException(
            status_code=404,
            detail="입력한 정보와 일치하는 구매 내역을 찾을 수 없습니다.",
        )

    payment_items = [
        TicketPaymentHistoryItem(
            payment_id=payment.id,
            display_order_id=payment.display_order_id,
            payment_name=payment.payment_name,
            amount=(
                payment.paid_amount
                if payment.paid_amount is not None
                else payment.expected_amount
            ),
            status=payment.status,
            status_name=get_payment_status_name(
                payment.status,
            ),
            paid_at=payment.paid_at,
        )
        for payment in visible_payments
    ]

    representative_user = ticket_users[0]

    return TicketPaymentHistoryResponse(
        name=representative_user.name,
        phone=mask_phone(
            representative_user.phone,
        ),
        payments=payment_items,
    )


def get_payment_status_code(payment_status: int) -> str:
    status_codes = {
        Payment.STATUS_READY: "READY",
        Payment.STATUS_PAID: "PAID",
        Payment.STATUS_FAILED: "FAILED",
        Payment.STATUS_CANCELED: "CANCELED",
    }

    return status_codes.get(
        payment_status,
        "UNKNOWN",
    )


def get_ticket_payment_status(
        db: Session,
        *,
        payment_id: int,
        ticket_user_id: int,
) -> TicketPaymentStatusResponse:
    payment = find_payment_by_id_and_ticket_user_id(
        db,
        payment_id=payment_id,
        ticket_user_id=ticket_user_id,
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="결제 정보를 찾을 수 없습니다.",
        )

    is_completed = payment.status in {
        Payment.STATUS_PAID,
        Payment.STATUS_FAILED,
        Payment.STATUS_CANCELED,
    }

    is_success = (
            payment.status == Payment.STATUS_PAID
    )

    amount = (
        payment.paid_amount
        if payment.paid_amount is not None
        else payment.expected_amount
    )

    return TicketPaymentStatusResponse(
        payment_id=payment.id,
        ticket_user_id=payment.ticket_user_id,
        status=payment.status,
        status_code=get_payment_status_code(
            payment.status,
        ),
        status_name=get_payment_status_name(
            payment.status,
        ),
        is_completed=is_completed,
        is_success=is_success,
        name=payment.ticket_user.name,
        display_order_id=payment.display_order_id,
        payment_name=payment.payment_name,
        amount=amount,
        quantity=1,
        paid_at=payment.paid_at,
    )



def get_ticket_user_for_admin(
        db: Session,
        *,
        ticket_user_id: int,
):
    ticket_user = find_ticket_user_by_id_for_admin(
        db,
        ticket_user_id=ticket_user_id,
    )

    if not ticket_user:
        raise HTTPException(
            status_code=404,
            detail="티켓 신청 정보를 찾을 수 없습니다.",
        )

    return ticket_user