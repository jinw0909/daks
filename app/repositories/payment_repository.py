from sqlalchemy.orm import Session

from app.db.models.payment import Payment


def create_ready_payment(
        db: Session,
        *,
        ticket_user_id: int,
        payment_name: str,
        expected_amount: int,
        toss_product_key: str,
) -> Payment:
    payment = Payment(
        ticket_user_id=ticket_user_id,
        status=Payment.STATUS_READY,
        payment_name=payment_name,
        expected_amount=expected_amount,
        paid_amount=None,
        toss_product_key=toss_product_key,
        toss_payment_key=None,
        raw_payload=None,
        paid_at=None,
        failed_at=None,
    )

    db.add(payment)
    db.flush()

    return payment