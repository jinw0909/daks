from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PublicSpeakerListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    english_name: str | None
    company_name: str
    public_title: str | None
    profile_image_url: str | None

    x_url: str | None
    youtube_url: str | None
    facebook_url: str | None

    display_order: int


class PublicSpeakerDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    english_name: str | None
    company_name: str
    public_title: str | None
    profile_image_url: str | None
    x_url: str | None
    youtube_url: str | None
    facebook_url: str | None
    display_order: int