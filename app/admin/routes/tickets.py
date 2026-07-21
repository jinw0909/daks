from math import ceil

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.admin.dependencies import resolve_admin_from_access_token
from app.admin.templates import templates
from app.api.deps import get_db
from app.repositories.ticket_user_repository import (
    count_ticket_users_for_admin,
    find_ticket_users_for_admin,
)
from app.services.ticket_service import (
    get_ticket_user_for_admin,
)


router = APIRouter(
    prefix="/tickets",
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


def get_latest_payment(ticket_user):
    if not ticket_user.payments:
        return None

    return max(
        ticket_user.payments,
        key=lambda payment: (
            payment.created_at,
            payment.id,
        ),
    )

@router.get(
    "",
    response_class=HTMLResponse,
)
def ticket_list_page(
        request: Request,
        page: int = Query(default=1, ge=1),
        payment_status: str | None = Query(default=None),
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

    parsed_payment_status: int | None = None

    if payment_status not in {
        None,
        "",
    }:
        try:
            parsed_payment_status = int(payment_status)

        except ValueError:
            parsed_payment_status = None

    page_size = 20
    offset = (page - 1) * page_size

    ticket_users = find_ticket_users_for_admin(
        db,
        keyword=keyword,
        payment_status=parsed_payment_status,
        offset=offset,
        limit=page_size,
    )

    total_count = count_ticket_users_for_admin(
        db,
        keyword=keyword,
        payment_status=parsed_payment_status,
    )

    total_pages = max(
        1,
        ceil(total_count / page_size),
    )

    # 존재하지 않는 페이지 번호가 들어온 경우
    if page > total_pages:
        return RedirectResponse(
            url="/admin/tickets",
            status_code=303,
        )

    ticket_rows = [
        {
            "ticket_user": ticket_user,
            "latest_payment": get_latest_payment(
                ticket_user,
            ),
            "payment_count": len(
                ticket_user.payments,
            ),
        }
        for ticket_user in ticket_users
    ]

    return templates.TemplateResponse(
        request=request,
        name="tickets/list.html",
        context={
            "admin": admin,
            "ticket_rows": ticket_rows,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "selected_payment_status": parsed_payment_status,
            "keyword": keyword or "",
        },
    )


@router.get(
    "/{ticket_user_id}",
    response_class=HTMLResponse,
)
def ticket_detail_page(
        ticket_user_id: int,
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
        ticket_user = get_ticket_user_for_admin(
            db,
            ticket_user_id=ticket_user_id,
        )

    except HTTPException:
        return templates.TemplateResponse(
            request=request,
            name="tickets/not_found.html",
            context={
                "admin": admin,
            },
            status_code=404,
        )

    payments = sorted(
        ticket_user.payments,
        key=lambda payment: (
            payment.created_at,
            payment.id,
        ),
        reverse=True,
    )

    return templates.TemplateResponse(
        request=request,
        name="tickets/detail.html",
        context={
            "admin": admin,
            "ticket_user": ticket_user,
            "payments": payments,
        },
    )