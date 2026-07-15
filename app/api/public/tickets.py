from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.schemas.ticket import (
    TicketPaymentHistoryRequest,
    TicketPaymentHistoryResponse,
    TicketPaymentPrepareRequest,
    TicketPaymentPrepareResponse, TicketPaymentStatusResponse,
)
from app.services.ticket_service import (
    get_ticket_payment_history,
    prepare_ticket_payment, get_ticket_payment_status,
)


router = APIRouter(
    prefix="/ticket-payments",
    tags=["Public Ticket Payments"],
)


@router.post(
    "/prepare",
    response_model=TicketPaymentPrepareResponse,
    status_code=status.HTTP_201_CREATED,
)
def prepare_payment(
        request: TicketPaymentPrepareRequest,
        db: DbSession,
) -> TicketPaymentPrepareResponse:
    return prepare_ticket_payment(
        db=db,
        request=request,
    )


@router.post(
    "/history",
    response_model=TicketPaymentHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="티켓 구매 내역 조회",
)
def get_payment_history(
        request: TicketPaymentHistoryRequest,
        db: DbSession,
) -> TicketPaymentHistoryResponse:
    return get_ticket_payment_history(
        db=db,
        request=request,
    )


@router.get(
    "/{payment_id}/status",
    response_model=TicketPaymentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="티켓 결제 상태 조회",
)
def get_payment_status(
        payment_id: int,
        ticket_user_id: int,
        db: DbSession,
) -> TicketPaymentStatusResponse:
    return get_ticket_payment_status(
        db=db,
        payment_id=payment_id,
        ticket_user_id=ticket_user_id,
    )