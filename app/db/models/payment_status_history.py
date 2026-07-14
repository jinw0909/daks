from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PaymentStatusHistory(Base):
    __tablename__ = "payment_status_history"

    __table_args__ = (
        Index(
            "ix_payment_status_history_payment_id",
            "payment_id",
        ),
        Index(
            "ix_payment_status_history_created_at",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    payment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "payments.id",
            name="fk_payment_status_history_payment",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    before_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    after_status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    actor: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="SYSTEM",
    )

    reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )