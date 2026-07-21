from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.payment_repository import (
    find_payment_by_id_for_admin,
    find_payment_status_histories,
)
from app.repositories.webhook_log_repository import (
    find_webhook_logs_by_payment_id,
)


def get_payment_admin_detail(
        db: Session,
        *,
        payment_id: int,
):
    payment = find_payment_by_id_for_admin(
        db,
        payment_id=payment_id,
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="결제 정보를 찾을 수 없습니다.",
        )

    histories = find_payment_status_histories(
        db,
        payment_id=payment_id,
    )

    webhook_logs = find_webhook_logs_by_payment_id(
        db,
        payment_id=payment_id,
    )

    return {
        "payment": payment,
        "histories": histories,
        "webhook_logs": webhook_logs,
    }