from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.schemas.ticket import (
    TicketPaymentHistoryRequest,
    TicketPaymentHistoryResponse,
    TicketPaymentPrepareRequest,
    TicketPaymentPrepareResponse,
)
from app.services.ticket_service import (
    get_ticket_payment_history,
    prepare_ticket_payment,
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