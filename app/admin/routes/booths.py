from math import ceil

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Form,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.admin.dependencies import resolve_admin_from_access_token
from app.admin.templates import templates
from app.api.deps import get_db
from app.repositories.booth_application_repository import (
    count_booth_applications,
    find_booth_applications,
)
from app.services.booth_application_service import (
    get_booth_application_or_404,
    update_booth_application_status,
)


router = APIRouter(
    prefix="/booths",
)


def resolve_admin_or_redirect(
        db: Session,
        access_token: str | None,
):
    admin = resolve_admin_from_access_token(
        db,
        access_token,
    )

    if not admin:
        return None, RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    return admin, None


@router.get(
    "",
    response_class=HTMLResponse,
)
def booth_list_page(
        request: Request,
        page: int = Query(default=1, ge=1),
        status: int | None = Query(default=None),
        keyword: str | None = Query(default=None),
        admin_access_token: str | None = Cookie(default=None),
        db: Session = Depends(get_db),
):
    admin, redirect = resolve_admin_or_redirect(
        db,
        admin_access_token,
    )

    if redirect:
        return redirect

    page_size = 20
    offset = (page - 1) * page_size

    applications = find_booth_applications(
        db,
        status=status,
        keyword=keyword,
        offset=offset,
        limit=page_size,
    )

    total_count = count_booth_applications(
        db,
        status=status,
        keyword=keyword,
    )

    total_pages = max(
        1,
        ceil(total_count / page_size),
    )

    return templates.TemplateResponse(
        request=request,
        name="booths/list.html",
        context={
            "admin": admin,
            "applications": applications,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "selected_status": status,
            "keyword": keyword or "",
        },
    )


@router.get(
    "/{application_id}",
    response_class=HTMLResponse,
)
def booth_detail_page(
        application_id: int,
        request: Request,
        admin_access_token: str | None = Cookie(default=None),
        db: Session = Depends(get_db),
):
    admin, redirect = resolve_admin_or_redirect(
        db,
        admin_access_token,
    )

    if redirect:
        return redirect

    try:
        application = get_booth_application_or_404(
            db,
            application_id,
        )

    except HTTPException:
        return templates.TemplateResponse(
            request=request,
            name="booths/not_found.html",
            context={
                "admin": admin,
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        request=request,
        name="booths/detail.html",
        context={
            "admin": admin,
            "application": application,
        },
    )


@router.post("/{application_id}/status")
def change_booth_status(
        application_id: int,
        status: int = Form(...),
        admin_access_token: str | None = Cookie(default=None),
        db: Session = Depends(get_db),
):
    admin, redirect = resolve_admin_or_redirect(
        db,
        admin_access_token,
    )

    if redirect:
        return redirect

    update_booth_application_status(
        db,
        application_id=application_id,
        status=status,
    )

    return RedirectResponse(
        url=f"/admin/booths/{application_id}",
        status_code=303,
    )