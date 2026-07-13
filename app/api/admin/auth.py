from fastapi import APIRouter, Cookie, Response

from app.api.deps import DbSession
from app.core.config import settings
from app.schemas.admin_auth import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminResponse,
)
from app.services.admin_auth_service import (
    login_admin,
    logout_admin,
    refresh_admin_access_token,
)


router = APIRouter(
    prefix="/auth",
    tags=["관리자 인증"],
)


def set_admin_auth_cookies(
        response: Response,
        *,
        access_token: str,
        refresh_token: str,
) -> None:
    response.set_cookie(
        key="admin_access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=(
                settings.admin_access_token_expire_minutes * 60
        ),
        path="/",
    )

    response.set_cookie(
        key="admin_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=(
                settings.admin_refresh_token_expire_days
                * 24
                * 60
                * 60
        ),
        path="/",
    )


@router.post(
    "/login",
    response_model=AdminLoginResponse,
)
def login(
        request: AdminLoginRequest,
        response: Response,
        db: DbSession,
) -> AdminLoginResponse:
    result = login_admin(
        db,
        username=request.username,
        password=request.password,
    )

    set_admin_auth_cookies(
        response,
        access_token=result.access_token,
        refresh_token=result.refresh_token,
    )

    return AdminLoginResponse(
        admin=AdminResponse.model_validate(result.admin),
    )


@router.post("/refresh")
def refresh(
        response: Response,
        db: DbSession,
        admin_refresh_token: str | None = Cookie(default=None),
):
    if not admin_refresh_token:
        return {
            "message": "리프레시 토큰이 없습니다.",
        }

    access_token = refresh_admin_access_token(
        db,
        admin_refresh_token,
    )

    response.set_cookie(
        key="admin_access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=(
                settings.admin_access_token_expire_minutes * 60
        ),
        path="/",
    )

    return {
        "message": "관리자 토큰이 갱신되었습니다.",
    }


@router.post("/logout")
def logout(
        response: Response,
        db: DbSession,
        admin_refresh_token: str | None = Cookie(default=None),
):
    logout_admin(
        db,
        admin_refresh_token,
    )

    response.delete_cookie(
        "admin_access_token",
        path="/",
    )

    response.delete_cookie(
        "admin_refresh_token",
        path="/",
    )

    return {
        "message": "로그아웃되었습니다.",
    }