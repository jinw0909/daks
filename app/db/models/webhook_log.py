from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WebhookLog(Base):
    __tablename__ = "webhook_log"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    order_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    payment_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    status: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    amount: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    method: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    payload: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    enrollmentid: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    ticketuser_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    receipt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    approved_at: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    datetime: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )