from math import ceil

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)
from sqlalchemy.orm import Session

from app.admin.dependencies import (
    resolve_admin_from_access_token,
)
from app.admin.templates import templates
from app.api.deps import get_db
from app.repositories.sponsor_repository import (
    count_sponsors,
    find_sponsors,
)
from app.services.sponsor_service import (
    SPONSOR_CATEGORY_LABELS,
    create_sponsor,
    get_sponsor_or_404,
    toggle_sponsor_active,
    update_sponsor, update_sponsor_logo_image, get_sponsor_payment_summary,
)


router = APIRouter(
    prefix="/sponsors",
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


def parse_optional_bool(
        value: str | None,
) -> bool | None:
    if value == "true":
        return True

    if value == "false":
        return False

    return None

def parse_optional_int(
        value: str | None,
) -> int | None:
    if value is None:
        return None

    normalized = value.strip()

    if not normalized:
        return None

    try:
        return int(normalized)
    except ValueError:
        return None

@router.get(
    "",
    response_class=HTMLResponse,
)
def sponsor_list_page(
        request: Request,
        page: int = Query(
            default=1,
            ge=1,
        ),
        keyword: str | None = Query(
            default=None,
        ),
        category: str | None = Query(
            default=None,
        ),
        active: str | None = Query(
            default=None,
        ),
        admin_access_token: str | None = Cookie(
            default=None,
        ),
        db: Session = Depends(get_db),
):
    admin, redirect = resolve_admin_or_redirect(
        db,
        admin_access_token,
    )

    if redirect:
        return redirect

    parsed_category = parse_optional_int(
        category
    )

    is_active = parse_optional_bool(
        active
    )

    page_size = 20
    offset = (page - 1) * page_size

    sponsors = find_sponsors(
        db,
        keyword=keyword,
        category=parsed_category,
        is_active=is_active,
        offset=offset,
        limit=page_size,
    )

    total_count = count_sponsors(
        db,
        keyword=keyword,
        category=parsed_category,
        is_active=is_active,
    )

    total_pages = max(
        1,
        ceil(total_count / page_size),
    )

    return templates.TemplateResponse(
        request=request,
        name="sponsors/list.html",
        context={
            "admin": admin,
            "sponsors": sponsors,
            "category_labels": SPONSOR_CATEGORY_LABELS,
            "total_count": total_count,
            "current_page": page,
            "total_pages": total_pages,
            "keyword": keyword or "",
            "selected_category": parsed_category,
            "selected_active": active or "",
        },
    )


@router.get(
    "/new",
    response_class=HTMLResponse,
)
def sponsor_create_page(
        request: Request,
        admin_access_token: str | None = Cookie(
            default=None,
        ),
        db: Session = Depends(get_db),
):
    admin, redirect = resolve_admin_or_redirect(
        db,
        admin_access_token,
    )

    if redirect:
        return redirect

    return templates.TemplateResponse(
        request=request,
        name="sponsors/form.html",
        context={
            "admin": admin,
            "sponsor": None,
            "category_labels": SPONSOR_CATEGORY_LABELS,
            "error": None,
            "form_action": "/admin/sponsors",
            "page_title": "스폰서 등록",
        },
    )


@router.post(
    "",
    response_class=HTMLResponse,
)
def sponsor_create_process(
        request: Request,
        name: str = Form(...),
        category: int = Form(...),
        logo_url: str | None = Form(
            default=None,
        ),
        website_url: str | None = Form(
            default=None,
        ),
        toss_product_key: str | None = Form(
            default=None,
        ),
        toss_product_link: str | None = Form(
            default=None,
        ),
        display_order: int = Form(
            default=0,
        ),
        is_active: bool = Form(
            default=False,
        ),
        admin_access_token: str | None = Cookie(
            default=None,
        ),
        db: Session = Depends(get_db),
):
    admin, redirect = resolve_admin_or_redirect(
        db,
        admin_access_token,
    )

    if redirect:
        return redirect

    try:
        sponsor = create_sponsor(
            db,
            name=name,
            category=category,
            logo_url=logo_url,
            website_url=website_url,
            toss_product_key=toss_product_key,
            toss_product_link=toss_product_link,
            display_order=display_order,
            is_active=is_active,
        )

    except HTTPException as exc:
        form_sponsor = {
            "name": name,
            "category": category,
            "logo_url": logo_url,
            "website_url": website_url,
            "toss_product_key": toss_product_key,
            "toss_product_link": toss_product_link,
            "display_order": display_order,
            "is_active": is_active,
        }

        return templates.TemplateResponse(
            request=request,
            name="sponsors/form.html",
            context={
                "admin": admin,
                "sponsor": form_sponsor,
                "category_labels": SPONSOR_CATEGORY_LABELS,
                "error": exc.detail,
                "form_action": "/admin/sponsors",
                "page_title": "스폰서 등록",
            },
            status_code=exc.status_code,
        )

    return RedirectResponse(
        url=f"/admin/sponsors/{sponsor.id}",
        status_code=303,
    )


@router.get(
    "/{sponsor_id}",
    response_class=HTMLResponse,
)
def sponsor_detail_page(
        sponsor_id: int,
        request: Request,
        admin_access_token: str | None = Cookie(
            default=None,
        ),
        db: Session = Depends(get_db),
):
    admin, redirect = resolve_admin_or_redirect(
        db,
        admin_access_token,
    )

    if redirect:
        return redirect

    try:
        sponsor = get_sponsor_or_404(
            db,
            sponsor_id,
        )

    except HTTPException:
        return templates.TemplateResponse(
            request=request,
            name="sponsors/not_found.html",
            context={
                "admin": admin,
            },
            status_code=404,
        )

    payment_summary = (
        get_sponsor_payment_summary(
            db,
            sponsor_id=sponsor.id,
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="sponsors/detail.html",
        context={
            "admin": admin,
            "sponsor": sponsor,
            "category_labels": SPONSOR_CATEGORY_LABELS,
            "payment_summary": payment_summary,
        },
    )


@router.get(
    "/{sponsor_id}/edit",
    response_class=HTMLResponse,
)
def sponsor_edit_page(
        sponsor_id: int,
        request: Request,
        admin_access_token: str | None = Cookie(
            default=None,
        ),
        db: Session = Depends(get_db),
):
    admin, redirect = resolve_admin_or_redirect(
        db,
        admin_access_token,
    )

    if redirect:
        return redirect

    try:
        sponsor = get_sponsor_or_404(
            db,
            sponsor_id,
        )

    except HTTPException:
        return templates.TemplateResponse(
            request=request,
            name="sponsors/not_found.html",
            context={
                "admin": admin,
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        request=request,
        name="sponsors/form.html",
        context={
            "admin": admin,
            "sponsor": sponsor,
            "category_labels": SPONSOR_CATEGORY_LABELS,
            "error": None,
            "form_action": (
                f"/admin/sponsors/{sponsor.id}"
            ),
            "page_title": "스폰서 수정",
        },
    )


@router.post(
    "/{sponsor_id}",
    response_class=HTMLResponse,
)
def sponsor_update_process(
        sponsor_id: int,
        request: Request,
        name: str = Form(...),
        category: int = Form(...),
        # logo_url: str | None = Form(
        #     default=None,
        # ),
        website_url: str | None = Form(
            default=None,
        ),
        toss_product_key: str | None = Form(
            default=None,
        ),
        toss_product_link: str | None = Form(
            default=None,
        ),
        display_order: int = Form(
            default=0,
        ),
        is_active: bool = Form(
            default=False,
        ),
        admin_access_token: str | None = Cookie(
            default=None,
        ),
        db: Session = Depends(get_db),
):
    admin, redirect = resolve_admin_or_redirect(
        db,
        admin_access_token,
    )

    if redirect:
        return redirect

    try:
        sponsor = update_sponsor(
            db,
            sponsor_id=sponsor_id,
            name=name,
            category=category,
            # logo_url=logo_url,
            website_url=website_url,
            toss_product_key=toss_product_key,
            toss_product_link=toss_product_link,
            display_order=display_order,
            is_active=is_active,
        )

    except HTTPException as exc:

        existing_sponsor = get_sponsor_or_404(
            db,
            sponsor_id,
        )

        form_sponsor = {
            "id": sponsor_id,
            "name": name,
            "category": category,
            "logo_url": existing_sponsor.logo_url,
            "website_url": website_url,
            "toss_product_key": toss_product_key,
            "toss_product_link": toss_product_link,
            "display_order": display_order,
            "is_active": is_active,
        }

        return templates.TemplateResponse(
            request=request,
            name="sponsors/form.html",
            context={
                "admin": admin,
                "sponsor": form_sponsor,
                "category_labels": SPONSOR_CATEGORY_LABELS,
                "error": exc.detail,
                "form_action": (
                    f"/admin/sponsors/{sponsor_id}"
                ),
                "page_title": "스폰서 수정",
            },
            status_code=exc.status_code,
        )

    return RedirectResponse(
        url=f"/admin/sponsors/{sponsor.id}",
        status_code=303,
    )

@router.post("/{sponsor_id}/logo-image")
async def upload_sponsor_logo(
        sponsor_id: int,
        image: UploadFile,
        admin_access_token: str | None = Cookie(
            default=None,
        ),
        db: Session = Depends(get_db),
):
    admin, redirect = resolve_admin_or_redirect(
        db,
        admin_access_token,
    )

    if redirect:
        return redirect

    await update_sponsor_logo_image(
        db,
        sponsor_id=sponsor_id,
        image=image,
    )

    return RedirectResponse(
        url=f"/admin/sponsors/{sponsor_id}/edit",
        status_code=303,
    )


@router.post(
    "/{sponsor_id}/toggle-active",
)
def sponsor_toggle_active_process(
        sponsor_id: int,
        admin_access_token: str | None = Cookie(
            default=None,
        ),
        db: Session = Depends(get_db),
):
    admin, redirect = resolve_admin_or_redirect(
        db,
        admin_access_token,
    )

    if redirect:
        return redirect

    sponsor = toggle_sponsor_active(
        db,
        sponsor_id=sponsor_id,
    )

    return RedirectResponse(
        url=f"/admin/sponsors/{sponsor.id}",
        status_code=303,
    )