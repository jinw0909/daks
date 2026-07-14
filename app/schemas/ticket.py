import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TicketPaymentPrepareRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

    phone: str = Field(
        min_length=10,
        max_length=11,
    )

    country: str | None = Field(
        default=None,
        max_length=100,
    )

    activity_type: str | None = Field(
        default=None,
        max_length=100,
    )

    registration_path: str | None = Field(
        default=None,
        max_length=100,
    )

    privacy_agreed: bool

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("연락처를 입력해주세요.")

        # 숫자를 제외한 하이픈, 공백, 괄호 등 제거
        phone = re.sub(r"\D", "", value)

        if not re.fullmatch(r"01[016789]\d{7,8}", phone):
            raise ValueError(
                "올바른 휴대전화 번호를 입력해주세요.",
            )

        return phone
class TicketPaymentPrepareResponse(BaseModel):
    ticket_user_id: int
    payment_id: int
    redirect_url: str



class TicketPaymentHistoryRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

    phone: str = Field(
        min_length=10,
        max_length=20,
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("성명을 입력해주세요.")

        return value

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        normalized = "".join(
            character
            for character in value
            if character.isdigit()
        )

        if len(normalized) not in {10, 11}:
            raise ValueError("올바른 연락처를 입력해주세요.")

        return normalized


class TicketPaymentHistoryItem(BaseModel):
    payment_id: int
    order_id: str | None
    payment_name: str
    amount: int
    status: int
    status_name: str
    paid_at: datetime | None


class TicketPaymentHistoryResponse(BaseModel):
    name: str
    phone: str
    payments: list[TicketPaymentHistoryItem]