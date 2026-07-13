from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import DbSession
from app.services.email_verification_service import (
    verify_application_email,
)


BASE_DIR = Path(__file__).resolve().parents[3]

templates = Jinja2Templates(
    directory=BASE_DIR / "app" / "templates",
)


router = APIRouter(
    prefix="/email-verifications",
    tags=["이메일 인증"],
)

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


@router.get(
    "/verify",
    response_class=HTMLResponse,
)
def verify_email(
        request: Request,
        db: DbSession,
        token: str = Query(min_length=20),
):
    try:
        verify_application_email(
            db,
            token,
        )

        return templates.TemplateResponse(
            request=request,
            name="email_verifications/success.html",
            context={},
        )

    except HTTPException as exc:
        return templates.TemplateResponse(
            request=request,
            name="email_verifications/error.html",
            context={
                "message": exc.detail,
            },
            status_code=exc.status_code,
        )