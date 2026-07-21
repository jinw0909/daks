# from sqlalchemy.orm import Session
# from sqlalchemy.sql.functions import func
#
# from app.db.models.ticket_user import TicketUser
#
#
# def create_ticket_user(
#         db: Session,
#         *,
#         name: str,
#         phone: str,
#         country: str | None,
#         activity_type: str | None,
#         registration_path: str | None,
#         privacy_agreed: bool,
# ) -> TicketUser:
#     ticket_user = TicketUser(
#         name=name,
#         phone=phone,
#         country=country,
#         activity_type=activity_type,
#         registration_path=registration_path,
#         phone_verified=False,
#         phone_verified_at=None,
#         privacy_agreed=privacy_agreed,
#     )
#
#     db.add(ticket_user)
#
#     # commit은 서비스에서 한 번에 한다.
#     # flush로 INSERT를 실행해서 id만 먼저 확보한다.
#     db.flush()
#
#     return ticket_user
#
# def find_ticket_users_by_name_and_phone(
#         db: Session,
#         *,
#         name: str,
#         phone: str,
# ) -> list[TicketUser]:
#     normalized_phone_column = func.replace(
#         func.replace(
#             TicketUser.phone,
#             "-",
#             "",
#         ),
#         " ",
#         "",
#     )
#
#     return (
#         db.query(TicketUser)
#         .filter(
#             TicketUser.name == name,
#             normalized_phone_column == phone,
#             )
#         .order_by(TicketUser.id.desc())
#         .all()
#     )

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.db.models.payment import Payment
from app.db.models.ticket_user import TicketUser


def create_ticket_user(
        db: Session,
        *,
        name: str,
        phone: str,
        country: str | None,
        activity_type: str | None,
        registration_path: str | None,
        privacy_agreed: bool,
) -> TicketUser:
    ticket_user = TicketUser(
        name=name,
        phone=phone,
        country=country,
        activity_type=activity_type,
        registration_path=registration_path,
        phone_verified=False,
        phone_verified_at=None,
        privacy_agreed=privacy_agreed,
    )

    db.add(ticket_user)

    # commit은 서비스에서 한 번에 한다.
    # flush로 INSERT를 실행해서 id만 먼저 확보한다.
    db.flush()

    return ticket_user


def find_ticket_users_by_name_and_phone(
        db: Session,
        *,
        name: str,
        phone: str,
) -> list[TicketUser]:
    normalized_phone_column = func.replace(
        func.replace(
            TicketUser.phone,
            "-",
            "",
        ),
        " ",
        "",
    )

    return (
        db.query(TicketUser)
        .filter(
            TicketUser.name == name,
            normalized_phone_column == phone,
            )
        .order_by(TicketUser.id.desc())
        .all()
    )


def find_ticket_users_for_admin(
        db: Session,
        *,
        keyword: str | None,
        payment_status: int | None,
        offset: int,
        limit: int,
) -> list[TicketUser]:
    query = (
        db.query(TicketUser)
        .options(
            selectinload(TicketUser.payments),
        )
    )

    if keyword:
        normalized_keyword = keyword.strip()

        if normalized_keyword:
            keyword_pattern = f"%{normalized_keyword}%"

            normalized_phone_column = func.replace(
                func.replace(
                    TicketUser.phone,
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

            conditions = [
                TicketUser.name.ilike(keyword_pattern),
                TicketUser.phone.ilike(keyword_pattern),
                TicketUser.country.ilike(keyword_pattern),
                TicketUser.activity_type.ilike(keyword_pattern),
                TicketUser.registration_path.ilike(keyword_pattern),
            ]

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
            TicketUser.payments.any(
                Payment.status == payment_status,
                )
        )

    return (
        query
        .order_by(
            TicketUser.created_at.desc(),
            TicketUser.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


def count_ticket_users_for_admin(
        db: Session,
        *,
        keyword: str | None,
        payment_status: int | None,
) -> int:
    query = db.query(
        func.count(TicketUser.id),
    )

    if keyword:
        normalized_keyword = keyword.strip()

        if normalized_keyword:
            keyword_pattern = f"%{normalized_keyword}%"

            normalized_phone_column = func.replace(
                func.replace(
                    TicketUser.phone,
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

            conditions = [
                TicketUser.name.ilike(keyword_pattern),
                TicketUser.phone.ilike(keyword_pattern),
                TicketUser.country.ilike(keyword_pattern),
                TicketUser.activity_type.ilike(keyword_pattern),
                TicketUser.registration_path.ilike(keyword_pattern),
            ]

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
            TicketUser.payments.any(
                Payment.status == payment_status,
                )
        )

    return query.scalar() or 0


def find_ticket_user_by_id_for_admin(
        db: Session,
        *,
        ticket_user_id: int,
) -> TicketUser | None:
    return (
        db.query(TicketUser)
        .options(
            selectinload(TicketUser.payments),
        )
        .filter(
            TicketUser.id == ticket_user_id,
            )
        .first()
    )