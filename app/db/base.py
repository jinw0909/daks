# app/db/base.py

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# from app.db.models import (  # noqa: E402, F401
#     Admin,
#     AdminRefreshToken,
#     BoothApplication,
#     Payment,
#     SpeakerApplication,
#     TicketUser,
#     WebhookLog,
# )