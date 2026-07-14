from sqlalchemy.orm import Session

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