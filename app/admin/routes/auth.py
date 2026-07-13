from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Form,
    Request,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.admin.dependencies import resolve_admin_from_access_token
from app.admin.templates import templates
from app.api.deps import get_db
from app.core.config import settings
from app.services.admin_auth_service import (
    login_admin,
    logout_admin,
)


router = APIRouter()


def set_admin_auth_cookies(
        response: RedirectResponse,
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


@router.get(
    "/login",
    response_class=HTMLResponse,
)
def login_page(
        request: Request,
        admin_access_token: str | None = Cookie(default=None),
        db: Session = Depends(get_db),
):
    admin = resolve_admin_from_access_token(
        db,
        admin_access_token,
    )

    if admin:
        return RedirectResponse(
            url="/admin",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "error": None,
        },
    )


@router.post(
    "/login",
    response_class=HTMLResponse,
)
def login_process(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db),
):
    try:
        result = login_admin(
            db,
            username=username.strip(),
            password=password,
        )

    except Exception as exc:
        detail = getattr(
            exc,
            "detail",
            "로그인에 실패했습니다.",
        )

        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "error": detail,
                "username": username,
            },
            status_code=401,
        )

    response = RedirectResponse(
        url="/admin",
        status_code=303,
    )

    set_admin_auth_cookies(
        response,
        access_token=result.access_token,
        refresh_token=result.refresh_token,
    )

    return response


@router.post("/logout")
def logout_process(
        db: Session = Depends(get_db),
        admin_refresh_token: str | None = Cookie(default=None),
):
    logout_admin(
        db,
        admin_refresh_token,
    )

    response = RedirectResponse(
        url="/admin/login",
        status_code=303,
    )

    response.delete_cookie(
        key="admin_access_token",
        path="/",
    )

    response.delete_cookie(
        key="admin_refresh_token",
        path="/",
    )

    return response