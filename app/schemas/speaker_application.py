from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SpeakerApplicationCreateRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

    company_name: str = Field(
        min_length=1,
        max_length=255,
    )

    email: EmailStr

    phone: str = Field(
        min_length=8,
        max_length=30,
    )

    social_url: str | None = Field(
        default=None,
        max_length=500,
    )

    presentation_content: str = Field(
        min_length=1,
        max_length=5000,
    )

    privacy_agreed: bool

    @field_validator(
        "name",
        "company_name",
        "phone",
        "social_url",
        "presentation_content",
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


class SpeakerApplicationAdminUpdateRequest(BaseModel):
    status: int | None = None
    english_name: str | None = Field(default=None, max_length=100)
    public_title: str | None = Field(default=None, max_length=255)
    profile_image_url: str | None = Field(default=None, max_length=500)
    x_url: str | None = Field(default=None, max_length=500)
    youtube_url: str | None = Field(default=None, max_length=500)
    is_public: bool | None = None
    display_order: int | None = None

class SpeakerApplicationCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company_name: str
    email: EmailStr
    status: int
    email_verified: bool
    created_at: datetime


class PublicSpeakerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    english_name: str | None
    company_name: str
    public_title: str | None
    profile_image_url: str | None
    x_url: str | None
    youtube_url: str | None
    display_order: int


class PublicSpeakerListResponse(BaseModel):
    items: list[PublicSpeakerResponse]

