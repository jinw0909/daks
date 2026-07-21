# app/admin/routes/statistics.py

from typing import Literal

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Query,
    Request,
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
from app.core.config import settings
from app.services.statistics_service import (
    TICKET_UNIT_PRICE,
    build_admin_statistics,
    get_quick_period_values,
)


router = APIRouter(
    prefix="/statistics",
)


StatisticsTab = Literal[
    "overview",
    "tickets",
    "sponsors",
]


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
def statistics_page(
        request: Request,
        tab: StatisticsTab = Query(
            default="overview",
        ),
        period: str | None = Query(
            default=None,
        ),
        received_from: str | None = Query(
            default=None,
        ),
        received_to: str | None = Query(
            default=None,
        ),
        sponsor_id: int | None = Query(
            default=None,
            ge=1,
        ),
        ticket_page: int = Query(
            default=1,
            ge=1,
        ),
        sponsor_page: int = Query(
            default=1,
            ge=1,
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

    selected_received_from = (
            received_from or ""
    )
    selected_received_to = (
            received_to or ""
    )

    selected_period = period or ""

    if period in {
        "today",
        "7days",
        "30days",
    }:
        (
            selected_received_from,
            selected_received_to,
        ) = get_quick_period_values(
            period,
        )

    elif period == "all":
        selected_received_from = ""
        selected_received_to = ""

    else:
        selected_period = ""

    statistics = build_admin_statistics(
        db,
        ticket_product_key=(
            settings
            .toss_ticket_product_key
            .strip()
        ),
        received_from=(
                selected_received_from
                or None
        ),
        received_to=(
                selected_received_to
                or None
        ),
        sponsor_id=sponsor_id,
        ticket_page=ticket_page,
        sponsor_page=sponsor_page,
        page_size=20,
    )

    return templates.TemplateResponse(
        request=request,
        name="statistics/index.html",
        context={
            "admin": admin,
            "active_menu": "statistics",

            "selected_tab": tab,
            "selected_period": selected_period,
            "selected_sponsor_id": sponsor_id,
            "selected_ticket_page": (
                statistics
                .tickets
                .transactions
                .current_page
            ),
            "selected_sponsor_page": (
                statistics
                .sponsors
                .selected_transactions
                .current_page
            ),

            "selected_received_from": (
                selected_received_from
            ),
            "selected_received_to": (
                selected_received_to
            ),

            "statistics": statistics,
            "overview": statistics.overview,
            "ticket_statistics": (
                statistics.tickets
            ),
            "sponsor_statistics": (
                statistics.sponsors
            ),

            "ticket_unit_price": (
                TICKET_UNIT_PRICE
            ),
        },
    )