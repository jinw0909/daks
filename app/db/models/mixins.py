# app/db/models/mixins.py

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

KST = ZoneInfo("Asia/Seoul")

def now_kst() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=now_kst,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=now_kst,
        onupdate=now_kst,
    )