# from sqlalchemy.orm import Session, joinedload
#
# from app.db.models.payment import Payment
#
#
# def create_ready_payment(
#         db: Session,
#         *,
#         ticket_user_id: int,
#         payment_name: str,
#         expected_amount: int,
#         toss_product_key: str,
# ) -> Payment:
#     payment = Payment(
#         ticket_user_id=ticket_user_id,
#         status=Payment.STATUS_READY,
#         payment_name=payment_name,
#         expected_amount=expected_amount,
#         paid_amount=None,
#         toss_product_key=toss_product_key,
#         toss_payment_key=None,
#         raw_payload=None,
#         paid_at=None,
#         failed_at=None,
#     )
#
#     db.add(payment)
#
#     # INSERT를 실행해서 autoincrement id를 받아온다.
#     db.flush()
#
#     # payment.display_order_id = f"2026{payment.id}"
#     payment.display_order_id = f"2026{payment.id:04d}"
#
#     # UPDATE를 DB에 반영한다.
#     db.flush()
#
#
#
#     return payment
#
#
# def find_payments_by_ticket_user_ids(
#         db: Session,
#         *,
#         ticket_user_ids: list[int],
# ) -> list[Payment]:
#     if not ticket_user_ids:
#         return []
#
#     return (
#         db.query(Payment)
#         .filter(
#             Payment.ticket_user_id.in_(ticket_user_ids),
#         )
#         .order_by(
#             Payment.created_at.desc(),
#             Payment.id.desc(),
#         )
#         .all()
#     )
#
#
# def find_payment_by_id_and_ticket_user_id(
#         db: Session,
#         *,
#         payment_id: int,
#         ticket_user_id: int,
# ) -> Payment | None:
#     return (
#         db.query(Payment)
#         .options(
#             joinedload(Payment.ticket_user),
#         )
#         .filter(
#             Payment.id == payment_id,
#             Payment.ticket_user_id == ticket_user_id,
#             )
#         .first()
#     )

from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session, joinedload

from app.db.models.payment import Payment
from app.db.models.payment_status_history import PaymentStatusHistory
from app.db.models.ticket_user import TicketUser


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

    payment.display_order_id = f"2026{payment.id:04d}"

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


def apply_admin_payment_filters(
        query,
        *,
        keyword: str | None,
        payment_status: int | None,
):
    if keyword:
        normalized_keyword = keyword.strip()

        if normalized_keyword:
            keyword_pattern = f"%{normalized_keyword}%"

            normalized_phone_column = func.replace(
                func.replace(
                    Payment.ticket_user.property.mapper.class_.phone,
                    "-",
                    "",
                ),
                " ",
                "",
            )

            normalized_phone_keyword = "".join(
                character
                for character in normalized_keyword
                if character.isdigit()
            )

            # ticket_user_model = (
            #     Payment.ticket_user.property.mapper.class_
            # )

            conditions = [
                Payment.display_order_id.ilike(
                    keyword_pattern,
                ),
                Payment.order_id.ilike(
                    keyword_pattern,
                ),
                Payment.toss_payment_key.ilike(
                    keyword_pattern,
                ),
                Payment.payment_name.ilike(
                    keyword_pattern,
                ),
                TicketUser.name.ilike(
                    keyword_pattern,
                ),
                TicketUser.phone.ilike(
                    keyword_pattern,
                ),
            ]

            if normalized_keyword.isdigit():
                conditions.append(
                    cast(Payment.id, String).ilike(
                        keyword_pattern,
                    )
                )

            if normalized_phone_keyword:
                conditions.append(
                    normalized_phone_column.ilike(
                        f"%{normalized_phone_keyword}%"
                    )
                )

            query = query.filter(
                or_(*conditions),
            )

    if payment_status is not None:
        query = query.filter(
            Payment.status == payment_status,
            )

    return query


def find_payments_for_admin(
        db: Session,
        *,
        keyword: str | None,
        payment_status: int | None,
        offset: int,
        limit: int,
) -> list[Payment]:
    query = (
        db.query(Payment)
        .join(Payment.ticket_user)
        .options(
            joinedload(Payment.ticket_user),
        )
    )

    query = apply_admin_payment_filters(
        query,
        keyword=keyword,
        payment_status=payment_status,
    )

    return (
        query
        .order_by(
            Payment.created_at.desc(),
            Payment.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


def count_payments_for_admin(
        db: Session,
        *,
        keyword: str | None,
        payment_status: int | None,
) -> int:
    query = (
        db.query(
            func.count(Payment.id),
        )
        .join(Payment.ticket_user)
    )

    query = apply_admin_payment_filters(
        query,
        keyword=keyword,
        payment_status=payment_status,
    )

    return query.scalar() or 0


def find_payment_by_id_for_admin(
        db: Session,
        *,
        payment_id: int,
) -> Payment | None:
    return (
        db.query(Payment)
        .options(
            joinedload(Payment.ticket_user),
        )
        .filter(
            Payment.id == payment_id,
            )
        .first()
    )


def find_payment_status_histories(
        db: Session,
        *,
        payment_id: int,
) -> list[PaymentStatusHistory]:
    return (
        db.query(PaymentStatusHistory)
        .filter(
            PaymentStatusHistory.payment_id == payment_id,
            )
        .order_by(
            PaymentStatusHistory.created_at.desc(),
            PaymentStatusHistory.id.desc(),
        )
        .all()
    )