from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import DbSession
from app.schemas.ticket import (
    TicketPaymentPrepareRequest,
    TicketPaymentPrepareResponse,
)
from app.services.ticket_service import prepare_ticket_payment


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