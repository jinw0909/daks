from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Request,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.admin.dependencies import resolve_admin_from_access_token
from app.admin.templates import templates
from app.api.deps import get_db


router = APIRouter()


@router.get(
    "/",
    response_class=HTMLResponse,
)
def dashboard(
        request: Request,
        admin_access_token: str | None = Cookie(default=None),
        db: Session = Depends(get_db),
):
    admin = resolve_admin_from_access_token(
        db,
        admin_access_token,
    )

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "admin": admin,
        },
    )