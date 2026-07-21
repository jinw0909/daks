from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin


class Sponsor(Base, TimestampMixin):
    __tablename__ = "sponsors"

    CATEGORY_PREMIUM = 1
    CATEGORY_GENERAL = 2
    CATEGORY_MEDIA_PARTNER = 3
    CATEGORY_ORGANIZER = 4

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    category: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment=(
            "1: 프리미엄 스폰서, "
            "2: 일반 스폰서, "
            "3: 미디어 파트너, "
            "4: 주최"
        ),
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    website_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    toss_product_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    toss_product_link: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )