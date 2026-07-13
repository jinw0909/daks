from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin


class BoothApplication(Base, TimestampMixin):
    __tablename__ = "booth_applications"

    STATUS_PENDING = 0
    STATUS_APPROVED = 1
    STATUS_REJECTED = 2

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    phone: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    contact_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    operation_plan: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=STATUS_PENDING,
        comment="0: 대기, 1: 승인, 2: 반려",
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    privacy_agreed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )