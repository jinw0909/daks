from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.payment_repository import create_ready_payment
from app.repositories.ticket_user_repository import create_ticket_user
from app.schemas.ticket import (
    TicketPaymentPrepareRequest,
    TicketPaymentPrepareResponse,
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