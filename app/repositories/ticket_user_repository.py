from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import func

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