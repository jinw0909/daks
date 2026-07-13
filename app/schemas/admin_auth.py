from pydantic import BaseModel, ConfigDict, Field


class AdminLoginRequest(BaseModel):
    username: str = Field(
        min_length=1,
        max_length=100,
    )

    password: str = Field(
        min_length=8,
        max_length=200,
    )


class AdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    is_active: bool


class AdminLoginResponse(BaseModel):
    admin: AdminResponse
    message: str = "로그인되었습니다."