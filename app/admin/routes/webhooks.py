import os
from math import ceil

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
from app.services.webhook_admin_service import (
    build_webhook_transactions,
    filter_webhook_transactions,
    get_transaction_histories,
    get_webhook_transaction,
    paginate_items,
)
from app.core.config import settings


router = APIRouter(
    prefix="/webhooks",
)

TOSS_TICKET_PRODUCT_KEY = (
    settings.toss_ticket_product_key.strip()
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
def webhook_list_page(
        request: Request,
        page: int = Query(
            default=1,
            ge=1,
        ),
        keyword: str | None = Query(
            default=None,
        ),
        source: str | None = Query(
            default=None,
        ),
        webhook_status: str | None = Query(
            default=None,
            alias="status",
        ),
        issue: str | None = Query(
            default=None,
        ),
        received_from: str | None = Query(
            default=None,
        ),
        received_to: str | None = Query(
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

    all_transactions = (
        build_webhook_transactions(
            db,
            ticket_product_key=(
                TOSS_TICKET_PRODUCT_KEY
            ),
        )
    )

    filtered_transactions = (
        filter_webhook_transactions(
            all_transactions,
            keyword=keyword,
            source=source,
            status=webhook_status,
            issue=issue,
            received_from=received_from,
            received_to=received_to,
        )
    )

    summary = {
        "total": len(
            filtered_transactions
        ),
        "normal": sum(
            1
            for item in filtered_transactions
            if not item.issue_code
        ),
        "issue": sum(
            1
            for item in filtered_transactions
            if item.issue_code
        ),
        "payment_id_missing": sum(
            1
            for item in filtered_transactions
            if item.issue_code
            == "PAYMENT_ID_MISSING"
        ),
        "payment_not_found": sum(
            1
            for item in filtered_transactions
            if item.issue_code
            == "PAYMENT_NOT_FOUND"
        ),
        "duplicate_payment": sum(
            1
            for item in filtered_transactions
            if item.issue_code
            == "DUPLICATE_PAYMENT"
        ),
        "payment_key_mismatch": sum(
            1
            for item in filtered_transactions
            if item.issue_code
            == "PAYMENT_KEY_MISMATCH"
        ),
    }

    page_size = 20

    page_items, total_count = paginate_items(
        filtered_transactions,
        page=page,
        page_size=page_size,
    )

    total_pages = max(
        1,
        ceil(total_count / page_size),
    )

    return templates.TemplateResponse(
        request=request,
        name="webhooks/list.html",
        context={
            "admin": admin,
            "transactions": page_items,
            "total_count": total_count,
            "issue_count": summary["issue"],
            "summary": summary,
            "current_page": page,
            "total_pages": total_pages,
            "keyword": keyword or "",
            "selected_source": source or "",
            "selected_status": (
                    webhook_status or ""
            ),
            "selected_issue": issue or "",
            "selected_received_from": (
                    received_from or ""
            ),
            "selected_received_to": (
                    received_to or ""
            ),
        },
    )


@router.get(
    "/{payment_key}",
    response_class=HTMLResponse,
)
def webhook_detail_page(
        payment_key: str,
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

    transaction = get_webhook_transaction(
        db,
        payment_key=payment_key,
        ticket_product_key=(
            TOSS_TICKET_PRODUCT_KEY
        ),
    )

    if not transaction:
        return templates.TemplateResponse(
            request=request,
            name="webhooks/not_found.html",
            context={
                "admin": admin,
            },
            status_code=404,
        )

    histories = get_transaction_histories(
        db,
        payment_key=payment_key,
    )

    return templates.TemplateResponse(
        request=request,
        name="webhooks/detail.html",
        context={
            "admin": admin,
            "transaction": transaction,
            "histories": histories,
        },
    )