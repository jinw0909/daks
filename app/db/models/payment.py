from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    STATUS_READY = 1
    STATUS_PAID = 2
    STATUS_FAILED = 3

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    ticket_user_id: Mapped[int] = mapped_column(
        ForeignKey("ticket_users.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=STATUS_READY,
        comment="1: 결제대기, 2: 결제완료, 3: 결제실패",
    )

    payment_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    expected_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    paid_amount: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    toss_product_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    toss_payment_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    raw_payload: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    ticket_user = relationship(
        "TicketUser",
        back_populates="payments",
    )