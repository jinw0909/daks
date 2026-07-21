import json
from math import ceil
from urllib.parse import urlencode

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
from app.repositories.payment_repository import (
    count_payments_for_admin,
    find_payments_for_admin,
)
from app.services.payment_service import (
    get_payment_admin_detail,
)


router = APIRouter(
    prefix="/payments",
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


def parse_payment_status(
        payment_status: str | None,
) -> int | None:
    if payment_status in {
        None,
        "",
    }:
        return None

    try:
        parsed_status = int(payment_status)

    except (TypeError, ValueError):
        return None

    if parsed_status not in {
        1,
        2,
        3,
        4,
    }:
        return None

    return parsed_status


def get_payment_status_name(
        payment_status: int,
) -> str:
    status_names = {
        1: "결제 대기",
        2: "결제 완료",
        3: "결제 실패",
        4: "결제 취소",
    }

    return status_names.get(
        payment_status,
        "상태 확인 필요",
    )


def mask_webhook_payload(
        payload_text: str | None,
) -> str | None:
    if not payload_text:
        return None

    try:
        payload = json.loads(payload_text)

    except (TypeError, ValueError, json.JSONDecodeError):
        return payload_text

    data = payload.get("data")

    if isinstance(data, dict):
        payment = data.get("payment")

        if isinstance(payment, dict):
            if payment.get("secret"):
                payment["secret"] = "********"

    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


def build_payment_list_url(
        *,
        page: int,
        keyword: str,
        payment_status: int | None,
) -> str:
    params: dict[str, str | int] = {
        "page": page,
    }

    if keyword:
        params["keyword"] = keyword

    if payment_status is not None:
        params["payment_status"] = payment_status

    return (
            "/admin/payments?"
            + urlencode(params)
    )


@router.get(
    "",
    response_class=HTMLResponse,
)
def payment_list_page(
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

    parsed_payment_status = parse_payment_status(
        payment_status,
    )

    normalized_keyword = (
        keyword.strip()
        if keyword
        else ""
    )

    page_size = 20

    total_count = count_payments_for_admin(
        db,
        keyword=normalized_keyword,
        payment_status=parsed_payment_status,
    )

    total_pages = max(
        1,
        ceil(total_count / page_size),
    )

    if page > total_pages:
        return RedirectResponse(
            url=build_payment_list_url(
                page=total_pages,
                keyword=normalized_keyword,
                payment_status=parsed_payment_status,
            ),
            status_code=303,
        )

    offset = (page - 1) * page_size

    payments = find_payments_for_admin(
        db,
        keyword=normalized_keyword,
        payment_status=parsed_payment_status,
        offset=offset,
        limit=page_size,
    )

    return templates.TemplateResponse(
        request=request,
        name="payments/list.html",
        context={
            "admin": admin,
            "payments": payments,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "selected_payment_status": parsed_payment_status,
            "keyword": normalized_keyword,
        },
    )


@router.get(
    "/{payment_id}",
    response_class=HTMLResponse,
)
def payment_detail_page(
        payment_id: int,
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
        result = get_payment_admin_detail(
            db,
            payment_id=payment_id,
        )

    except HTTPException:
        return templates.TemplateResponse(
            request=request,
            name="payments/not_found.html",
            context={
                "admin": admin,
            },
            status_code=404,
        )

    payment = result["payment"]
    histories = result["histories"]
    webhook_logs = result["webhook_logs"]

    webhook_rows = [
        {
            "log": webhook_log,
            "masked_payload": mask_webhook_payload(
                webhook_log.payload,
            ),
        }
        for webhook_log in webhook_logs
    ]

    return templates.TemplateResponse(
        request=request,
        name="payments/detail.html",
        context={
            "admin": admin,
            "payment": payment,
            "histories": histories,
            "webhook_rows": webhook_rows,
            "get_payment_status_name": get_payment_status_name,
            "masked_payment_payload": mask_webhook_payload(
                payment.raw_payload,
            ),
        },
    )