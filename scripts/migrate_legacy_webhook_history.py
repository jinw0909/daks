from __future__ import annotations

import argparse
import base64
import copy
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.webhook_log import WebhookLog
from app.db.models.webhook_log_history import WebhookLogHistory
from app.db.session import SessionLocal


TOSS_API_BASE_URL = "https://api.tosspayments.com"
EVENT_TYPE = "ORDER_PAYMENT_STATUS_CHANGED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "webhook_log의 불완전한 과거 결제 데이터를 "
            "Toss 주문 조회 API로 보완하여 "
            "webhook_log_history에 삽입합니다."
        )
    )

    parser.add_argument(
        "--ids",
        type=str,
        default=None,
        help="webhook_log ID 목록. 예: 221,222,223",
    )

    parser.add_argument(
        "--min-id",
        type=int,
        default=None,
        help="webhook_log 최소 ID",
    )

    parser.add_argument(
        "--max-id",
        type=int,
        default=None,
        help="webhook_log 최대 ID",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="토스 요청 간 대기 시간. 기본값 0.2초",
    )

    parser.add_argument(
        "--commit",
        action="store_true",
        help="실제로 webhook_log_history에 INSERT합니다.",
    )

    parser.add_argument(
        "--include-complete",
        action="store_true",
        help=(
            "payload와 payment_key가 이미 있는 webhook_log도 "
            "조회 대상에 포함합니다."
        ),
    )

    return parser.parse_args()


def parse_ids(value: str | None) -> list[int] | None:
    if not value:
        return None

    result: list[int] = []

    for raw_item in value.split(","):
        item = raw_item.strip()

        if not item:
            continue

        try:
            result.append(int(item))
        except ValueError as exc:
            raise ValueError(
                f"잘못된 ID 값입니다: {item}"
            ) from exc

    return result or None


def build_authorization_header(secret_key: str) -> str:
    encoded = base64.b64encode(
        f"{secret_key}:".encode("utf-8")
    ).decode("ascii")

    return f"Basic {encoded}"


def fetch_toss_order(
        *,
        secret_key: str,
        order_id: str,
) -> dict[str, Any]:
    encoded_order_id = urllib.parse.quote(
        order_id,
        safe="",
    )

    url = (
        f"{TOSS_API_BASE_URL}"
        f"/v1/orders/{encoded_order_id}"
    )

    request = urllib.request.Request(
        url=url,
        method="GET",
        headers={
            "Authorization": build_authorization_header(
                secret_key
            ),
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
                request,
                timeout=20,
        ) as response:
            body = response.read().decode("utf-8")

    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"Toss HTTP {exc.code}: {error_body}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Toss 연결 실패: {exc}"
        ) from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Toss 응답을 JSON으로 파싱할 수 없습니다."
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            "Toss 주문 응답이 JSON 객체가 아닙니다."
        )

    return data


def parse_iso_datetime(
        value: str | None,
) -> datetime | None:
    if not value:
        return None

    parsed = datetime.fromisoformat(value)

    # 현재 모델이 timezone 없는 DateTime이므로
    # +09:00의 시각값은 유지하고 tzinfo만 제거
    return parsed.replace(tzinfo=None)


def get_latest_cancel_at(
        payment: dict[str, Any],
) -> str | None:
    cancels = payment.get("cancels") or []

    cancel_dates = [
        item.get("canceledAt")
        for item in cancels
        if isinstance(item, dict)
           and item.get("canceledAt")
    ]

    if not cancel_dates:
        return None

    return max(cancel_dates)


def get_event_at(
        order_data: dict[str, Any],
) -> str | None:
    payment = order_data.get("payment") or {}
    status = payment.get("status")

    if status in {
        "CANCELED",
        "PARTIAL_CANCELED",
    }:
        canceled_at = get_latest_cancel_at(payment)

        if canceled_at:
            return canceled_at

    return (
            payment.get("approvedAt")
            or payment.get("requestedAt")
            or order_data.get("createdAt")
    )


def sanitize_order_data(
        order_data: dict[str, Any],
) -> dict[str, Any]:
    sanitized = copy.deepcopy(order_data)

    payment = sanitized.get("payment")

    if isinstance(payment, dict):
        # 관리자 집계에 필요하지 않은 결제 비밀값 제거
        payment.pop("secret", None)

    return sanitized


def extract_first_product(
        order_data: dict[str, Any],
) -> dict[str, Any]:
    order_items = order_data.get("orderItems") or []

    if not order_items:
        return {}

    first_item = order_items[0]

    if not isinstance(first_item, dict):
        return {}

    product = first_item.get("product") or {}

    return product if isinstance(product, dict) else {}


def find_source_rows(
        db: Session,
        *,
        ids: list[int] | None,
        min_id: int | None,
        max_id: int | None,
        include_complete: bool,
) -> list[WebhookLog]:
    query = (
        db.query(WebhookLog)
        .filter(
            WebhookLog.order_id.isnot(None),
            WebhookLog.order_id != "",
            )
    )

    if ids:
        query = query.filter(
            WebhookLog.id.in_(ids)
        )

    if min_id is not None:
        query = query.filter(
            WebhookLog.id >= min_id
        )

    if max_id is not None:
        query = query.filter(
            WebhookLog.id <= max_id
        )

    if not include_complete:
        query = query.filter(
            or_(
                WebhookLog.payload.is_(None),
                WebhookLog.payload == "",
                WebhookLog.payment_key.is_(None),
                WebhookLog.payment_key == "",
                )
        )

    return (
        query
        .order_by(WebhookLog.id.asc())
        .all()
    )


def history_already_exists(
        db: Session,
        *,
        payment_key: str,
        status: str | None,
) -> bool:
    query = (
        db.query(WebhookLogHistory.id)
        .filter(
            WebhookLogHistory.eventType
            == EVENT_TYPE,
            WebhookLogHistory.payment_key
            == payment_key,
            )
    )

    if status is None:
        query = query.filter(
            WebhookLogHistory.status.is_(None)
        )
    else:
        query = query.filter(
            WebhookLogHistory.status == status
        )

    return query.first() is not None


def build_history(
        *,
        source: WebhookLog,
        order_data: dict[str, Any],
) -> WebhookLogHistory:
    sanitized_order = sanitize_order_data(
        order_data
    )

    payment = sanitized_order.get("payment") or {}

    if not isinstance(payment, dict):
        payment = {}

    product = extract_first_product(
        sanitized_order
    )

    event_at = get_event_at(
        sanitized_order
    )

    payload = {
        "createdAt": event_at,
        "eventType": EVENT_TYPE,
        "data": sanitized_order,
    }

    amount = sanitized_order.get("amount")

    name = (
            sanitized_order.get("customerName")
            or source.name
    )

    return WebhookLogHistory(
        eventType=EVENT_TYPE,
        order_id=(
                sanitized_order.get("orderKey")
                or source.order_id
        ),
        payment_key=payment.get("paymentKey"),
        status=payment.get("status"),
        amount=(
            str(amount)
            if amount is not None
            else None
        ),
        method=payment.get("method"),
        payload=json.dumps(
            payload,
            ensure_ascii=False,
        ),
        enrollmentid=None,
        name=name,
        ticketuser_id=None,
        product_key=product.get("productKey"),
        product_name=product.get("name"),
        approved_at=payment.get("approvedAt"),
        created_at=sanitized_order.get("createdAt"),
        datetime=parse_iso_datetime(event_at),
    )


def print_preview(
        *,
        source: WebhookLog,
        history: WebhookLogHistory,
) -> None:
    preview = {
        "source_webhook_log_id": source.id,
        "eventType": history.eventType,
        "order_id": history.order_id,
        "payment_key": history.payment_key,
        "status": history.status,
        "amount": history.amount,
        "method": history.method,
        "name": history.name,
        "product_key": history.product_key,
        "product_name": history.product_name,
        "approved_at": history.approved_at,
        "created_at": history.created_at,
        "datetime": (
            history.datetime.isoformat()
            if history.datetime
            else None
        ),
    }

    print(
        json.dumps(
            preview,
            ensure_ascii=False,
            indent=2,
        )
    )


def validate_selection(
        args: argparse.Namespace,
) -> None:
    if (
            args.ids is None
            and args.min_id is None
            and args.max_id is None
    ):
        raise ValueError(
            "안전을 위해 --ids 또는 "
            "--min-id/--max-id 범위를 지정해야 합니다."
        )


def main() -> None:
    args = parse_args()

    try:
        validate_selection(args)
        ids = parse_ids(args.ids)
    except ValueError as exc:
        print(
            f"입력 오류: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    secret_key = os.getenv("TOSS_SECRET_KEY")

    if not secret_key:
        print(
            "TOSS_SECRET_KEY 환경변수가 없습니다.",
            file=sys.stderr,
        )
        sys.exit(1)

    db = SessionLocal()

    success_count = 0
    skip_count = 0
    failure_count = 0

    try:
        source_rows = find_source_rows(
            db,
            ids=ids,
            min_id=args.min_id,
            max_id=args.max_id,
            include_complete=args.include_complete,
        )

        mode = (
            "COMMIT"
            if args.commit
            else "DRY-RUN"
        )

        print(f"실행 모드: {mode}")
        print(f"조회 대상: {len(source_rows)}건")
        print()

        for index, source in enumerate(
                source_rows,
                start=1,
        ):
            order_id = source.order_id

            print(
                f"[{index}/{len(source_rows)}] "
                f"webhook_log.id={source.id}, "
                f"order_id={order_id}"
            )

            if not order_id:
                print("  SKIP: order_id 없음")
                skip_count += 1
                continue

            try:
                order_data = fetch_toss_order(
                    secret_key=secret_key,
                    order_id=order_id,
                )

                history = build_history(
                    source=source,
                    order_data=order_data,
                )

                if not history.payment_key:
                    raise RuntimeError(
                        "토스 응답에 paymentKey가 없습니다."
                    )

                if history_already_exists(
                        db,
                        payment_key=history.payment_key,
                        status=history.status,
                ):
                    print(
                        "  SKIP: 동일한 "
                        "payment_key + status 이력 존재"
                    )
                    skip_count += 1
                    continue

                print_preview(
                    source=source,
                    history=history,
                )

                if args.commit:
                    db.add(history)
                    db.commit()
                    db.refresh(history)

                    print(
                        "  INSERT 완료: "
                        f"webhook_log_history.id="
                        f"{history.id}"
                    )
                else:
                    print("  DRY-RUN: INSERT하지 않음")

                success_count += 1

            except (
                    RuntimeError,
                    SQLAlchemyError,
                    ValueError,
            ) as exc:
                db.rollback()

                failure_count += 1

                print(
                    f"  실패: {exc}",
                    file=sys.stderr,
                )

            except Exception as exc:
                db.rollback()

                failure_count += 1

                print(
                    f"  예상하지 못한 실패: {exc}",
                    file=sys.stderr,
                )

            print()

            if args.delay > 0:
                time.sleep(args.delay)

    finally:
        db.close()

    print("=" * 50)
    print(f"성공: {success_count}건")
    print(f"건너뜀: {skip_count}건")
    print(f"실패: {failure_count}건")
    print(
        "DB 반영 여부: "
        + (
            "반영됨"
            if args.commit
            else "반영 안 됨"
        )
    )


if __name__ == "__main__":
    main()