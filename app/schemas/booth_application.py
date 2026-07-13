from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class BoothApplicationCreateRequest(BaseModel):
    company_name: str = Field(
        min_length=1,
        max_length=255,
    )

    email: EmailStr

    phone: str = Field(
        min_length=8,
        max_length=30,
    )

    contact_name: str = Field(
        min_length=1,
        max_length=100,
    )

    operation_plan: str = Field(
        min_length=1,
        max_length=5000,
    )

    privacy_agreed: bool

    @field_validator(
        "company_name",
        "phone",
        "contact_name",
        "operation_plan",
        mode="before",
    )
    @classmethod
    def strip_string(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value if value else None

        return value

    @field_validator("privacy_agreed")
    @classmethod
    def validate_privacy_agreed(cls, value: bool) -> bool:
        if not value:
            raise ValueError("개인정보 수집 및 이용에 동의해야 합니다.")

        return value


class BoothApplicationCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    contact_name: str
    email: EmailStr
    status: int
    email_verified: bool
    created_at: datetime