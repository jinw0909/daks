from sqlalchemy.orm import Session, joinedload

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

    # INSERT를 실행해서 autoincrement id를 받아온다.
    db.flush()

    payment.display_order_id = f"2026{payment.id}"

    # UPDATE를 DB에 반영한다.
    db.flush()



    return payment


def find_payments_by_ticket_user_ids(
        db: Session,
        *,
        ticket_user_ids: list[int],
) -> list[Payment]:
    if not ticket_user_ids:
        return []

    return (
        db.query(Payment)
        .filter(
            Payment.ticket_user_id.in_(ticket_user_ids),
        )
        .order_by(
            Payment.created_at.desc(),
            Payment.id.desc(),
        )
        .all()
    )


def find_payment_by_id_and_ticket_user_id(
        db: Session,
        *,
        payment_id: int,
        ticket_user_id: int,
) -> Payment | None:
    return (
        db.query(Payment)
        .options(
            joinedload(Payment.ticket_user),
        )
        .filter(
            Payment.id == payment_id,
            Payment.ticket_user_id == ticket_user_id,
            )
        .first()
    )