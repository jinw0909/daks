from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin


class TicketUser(Base, TimestampMixin):
    __tablename__ = "ticket_users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    activity_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    registration_path: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    phone_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    privacy_agreed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    payments = relationship(
        "Payment",
        back_populates="ticket_user",
    )