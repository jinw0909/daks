import re

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