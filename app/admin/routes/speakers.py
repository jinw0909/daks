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
from app.repositories.speaker_application_repository import (
    count_speaker_applications,
    find_speaker_applications,
)
from app.services.speaker_application_service import (
    get_speaker_application_or_404,
    update_speaker_application_status,
    update_speaker_public_profile, update_speaker_profile_image,
)
from fastapi import UploadFile

router = APIRouter(
    prefix="/speakers",
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
def speaker_list_page(
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

    applications = find_speaker_applications(
        db,
        status=status,
        keyword=keyword,
        offset=offset,
        limit=page_size,
    )

    total_count = count_speaker_applications(
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
        name="speakers/list.html",
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
def speaker_detail_page(
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
        application = get_speaker_application_or_404(
            db,
            application_id,
        )

    except HTTPException:
        return templates.TemplateResponse(
            request=request,
            name="speakers/not_found.html",
            context={
                "admin": admin,
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        request=request,
        name="speakers/detail.html",
        context={
            "admin": admin,
            "application": application,
            "error": None,
        },
    )


@router.post(
    "/{application_id}/status",
    response_class=HTMLResponse,
)
def change_speaker_status(
        application_id: int,
        request: Request,
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

    try:
        update_speaker_application_status(
            db,
            application_id=application_id,
            status=status,
        )

    except HTTPException as exc:
        application = get_speaker_application_or_404(
            db,
            application_id,
        )

        return templates.TemplateResponse(
            request=request,
            name="speakers/detail.html",
            context={
                "admin": admin,
                "application": application,
                "error": exc.detail,
            },
            status_code=exc.status_code,
        )

    return RedirectResponse(
        url=f"/admin/speakers/{application_id}",
        status_code=303,
    )

#
# @router.post("/{application_id}/public-profile")
# def change_speaker_public_profile(
#         application_id: int,
#         english_name: str | None = Form(default=None),
#         public_title: str | None = Form(default=None),
#         # profile_image_url: str | None = Form(default=None),
#         x_url: str | None = Form(default=None),
#         youtube_url: str | None = Form(default=None),
#         display_order: int = Form(default=0),
#         is_public: bool = Form(default=False),
#         admin_access_token: str | None = Cookie(default=None),
#         db: Session = Depends(get_db),
# ):
#     admin, redirect = resolve_admin_or_redirect(
#         db,
#         admin_access_token,
#     )
#
#     if redirect:
#         return redirect
#
#     update_speaker_public_profile(
#         db,
#         application_id=application_id,
#         english_name=english_name.strip() if english_name else None,
#         public_title=public_title.strip() if public_title else None,
#         # profile_image_url=(
#         #     profile_image_url.strip()
#         #     if profile_image_url
#         #     else None
#         # ),
#         x_url=x_url.strip() if x_url else None,
#         youtube_url=(
#             youtube_url.strip()
#             if youtube_url
#             else None
#         ),
#         display_order=display_order,
#         is_public=is_public,
#     )
#
#     return RedirectResponse(
#         url=f"/admin/speakers/{application_id}",
#         status_code=303,
#     )
@router.post(
    "/{application_id}/public-profile",
    response_class=HTMLResponse,
)
def change_speaker_public_profile(
        application_id: int,
        request: Request,
        english_name: str | None = Form(default=None),
        public_title: str | None = Form(default=None),
        x_url: str | None = Form(default=None),
        youtube_url: str | None = Form(default=None),
        display_order: int = Form(default=0),
        is_public: bool = Form(default=False),
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
        update_speaker_public_profile(
            db,
            application_id=application_id,
            english_name=(
                english_name.strip()
                if english_name
                else None
            ),
            public_title=(
                public_title.strip()
                if public_title
                else None
            ),
            x_url=x_url.strip() if x_url else None,
            youtube_url=(
                youtube_url.strip()
                if youtube_url
                else None
            ),
            display_order=display_order,
            is_public=is_public,
        )

    except HTTPException as exc:
        application = get_speaker_application_or_404(
            db,
            application_id,
        )

        return templates.TemplateResponse(
            request=request,
            name="speakers/detail.html",
            context={
                "admin": admin,
                "application": application,
                "error": exc.detail,
            },
            status_code=exc.status_code,
        )

    return RedirectResponse(
        url=f"/admin/speakers/{application_id}",
        status_code=303,
    )

@router.post("/{application_id}/profile-image")
async def upload_speaker_image(
        application_id: int,
        image: UploadFile,
        admin_access_token: str | None = Cookie(default=None),
        db: Session = Depends(get_db),
):
    admin, redirect = resolve_admin_or_redirect(
        db,
        admin_access_token,
    )

    if redirect:
        return redirect

    await update_speaker_profile_image(
        db,
        application_id=application_id,
        image=image,
    )

    return RedirectResponse(
        url=f"/admin/speakers/{application_id}",
        status_code=303,
    )