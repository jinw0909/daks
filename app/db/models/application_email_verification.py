from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin


class ApplicationEmailVerification(Base, TimestampMixin):
    __tablename__ = "application_email_verifications"

    TYPE_SPEAKER = 1
    TYPE_BOOTH = 2

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    application_type: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="1: 연사 신청, 2: 부스 신청",
    )

    application_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    invalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )