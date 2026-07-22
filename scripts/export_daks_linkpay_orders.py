from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


TOSS_API_BASE_URL = "https://api.tosspayments.com"

DAKS_PRODUCT_KEYS = {
    # 일반 DAKS 티켓
    "c43f5fac3ceb42989f66095ca5df5aa2",

    # DAKS Bullbit 티켓
    "524b5eb9685b423594cde3536c1807ae",
}

DAKS_PRODUCT_NAMES = {
    "2026  DIGITAL ASSET KOREA SUMMIT",
    "2026 DIGITAL ASSET KOREA SUMMIT",
    "2026  DIGITAL ASSET KOREA SUMMIT (Bullbit)",
    "2026 DIGITAL ASSET KOREA SUMMIT (Bullbit)",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Toss LinkPay 전체 주문을 조회하고 "
            "DAKS 일반 티켓과 Bullbit 티켓만 추출합니다."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="페이지당 조회 개수. 기본값 100",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="페이지 요청 간 대기 시간. 기본값 0.2초",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="exports",
        help="결과 저장 디렉터리. 기본값 exports",
    )

    parser.add_argument(
        "--include-unpaid",
        action="store_true",
        help="payment=null인 미결제 주문도 결과에 포함합니다.",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="테스트용 최대 페이지 수",
    )

    return parser.parse_args()


def build_authorization_header(secret_key: str) -> str:
    encoded = base64.b64encode(
        f"{secret_key}:".encode("utf-8")
    ).decode("ascii")

    return f"Basic {encoded}"


def request_orders_page(
        *,
        secret_key: str,
        limit: int,
        starting_after: str | None,
) -> list[dict[str, Any]]:
    params: dict[str, str | int] = {
        "limit": limit,
    }

    if starting_after:
        params["startingAfter"] = starting_after

    query_string = urllib.parse.urlencode(params)
    url = f"{TOSS_API_BASE_URL}/v1/orders?{query_string}"

    request = urllib.request.Request(
        url=url,
        method="GET",
        headers={
            "Authorization": build_authorization_header(secret_key),
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
                request,
                timeout=30,
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

    if not isinstance(data, list):
        raise RuntimeError(
            "Toss 주문 목록 응답이 배열이 아닙니다."
        )

    return [
        item
        for item in data
        if isinstance(item, dict)
    ]


def fetch_all_orders(
        *,
        secret_key: str,
        limit: int,
        delay: float,
        max_pages: int | None,
) -> list[dict[str, Any]]:
    all_orders: list[dict[str, Any]] = []

    starting_after: str | None = None
    page = 1

    seen_order_keys: set[str] = set()

    while True:
        if max_pages is not None and page > max_pages:
            print(
                f"최대 페이지 수 {max_pages}에 도달하여 중단"
            )
            break

        print(
            f"[페이지 {page}] 요청 중"
            + (
                f" startingAfter={starting_after}"
                if starting_after
                else ""
            )
        )

        orders = request_orders_page(
            secret_key=secret_key,
            limit=limit,
            starting_after=starting_after,
        )

        print(f"  응답: {len(orders)}건")

        if not orders:
            break

        new_count = 0

        for order in orders:
            order_key = order.get("orderKey")

            if not order_key:
                continue

            if order_key in seen_order_keys:
                continue

            seen_order_keys.add(order_key)
            all_orders.append(order)
            new_count += 1

        if new_count == 0:
            print(
                "  새 주문이 없어 무한 반복 방지를 위해 중단"
            )
            break

        if len(orders) < limit:
            print("마지막 페이지 도달")
            break

        last_order_key = orders[-1].get("orderKey")

        if not last_order_key:
            print(
                "마지막 주문에 orderKey가 없어 중단"
            )
            break

        if last_order_key == starting_after:
            print(
                "startingAfter 값이 반복되어 중단"
            )
            break

        starting_after = last_order_key
        page += 1

        if delay > 0:
            time.sleep(delay)

    return all_orders


def get_first_order_item(
        order: dict[str, Any],
) -> dict[str, Any] | None:
    order_items = order.get("orderItems") or []

    if not isinstance(order_items, list):
        return None

    for item in order_items:
        if isinstance(item, dict):
            return item

    return None


def get_product(
        order_item: dict[str, Any] | None,
) -> dict[str, Any]:
    if not order_item:
        return {}

    product = order_item.get("product")

    if not isinstance(product, dict):
        return {}

    return product


def is_daks_order(
        order: dict[str, Any],
) -> bool:
    order_items = order.get("orderItems") or []

    if not isinstance(order_items, list):
        return False

    for item in order_items:
        if not isinstance(item, dict):
            continue

        product = item.get("product")

        if not isinstance(product, dict):
            continue

        product_key = product.get("productKey")
        product_name = product.get("name")

        if product_key in DAKS_PRODUCT_KEYS:
            return True

        if product_name in DAKS_PRODUCT_NAMES:
            return True

    return False


def classify_product(
        product_key: str | None,
        product_name: str | None,
) -> str:
    if (
            product_key
            == "524b5eb9685b423594cde3536c1807ae"
            or "Bullbit" in (product_name or "")
    ):
        return "DAKS_BULLBIT"

    if (
            product_key
            == "c43f5fac3ceb42989f66095ca5df5aa2"
            or "DIGITAL ASSET KOREA SUMMIT"
            in (product_name or "")
    ):
        return "DAKS"

    return "UNKNOWN"


def normalize_order(
        order: dict[str, Any],
) -> dict[str, Any]:
    order_item = get_first_order_item(order)
    product = get_product(order_item)

    payment = order.get("payment")

    if not isinstance(payment, dict):
        payment = {}

    cancels = payment.get("cancels") or []

    if not isinstance(cancels, list):
        cancels = []

    cancel_amount = sum(
        int(cancel.get("cancelAmount") or 0)
        for cancel in cancels
        if isinstance(cancel, dict)
    )

    latest_cancel_at = None

    cancel_dates = [
        cancel.get("canceledAt")
        for cancel in cancels
        if isinstance(cancel, dict)
           and cancel.get("canceledAt")
    ]

    if cancel_dates:
        latest_cancel_at = max(cancel_dates)

    product_key = product.get("productKey")
    product_name = product.get("name")

    quantity = None

    if order_item:
        quantity = order_item.get("quantity")

    return {
        "category": classify_product(
            product_key,
            product_name,
        ),
        "order_key": order.get("orderKey"),
        "order_created_at": order.get("createdAt"),
        "customer_name": order.get("customerName"),
        "customer_phone": order.get(
            "customerPhoneNumber"
        ),
        "product_key": product_key,
        "product_name": product_name,
        "quantity": quantity,
        "order_amount": order.get("amount"),
        "payment_key": payment.get("paymentKey"),
        "payment_status": payment.get("status"),
        "payment_method": payment.get("method"),
        "requested_at": payment.get("requestedAt"),
        "approved_at": payment.get("approvedAt"),
        "latest_canceled_at": latest_cancel_at,
        "cancel_amount": cancel_amount,
        "balance_amount": payment.get(
            "balanceAmount"
        ),
        "receipt_url": (
                payment.get("receipt") or {}
        ).get("url"),
        "has_payment": bool(payment),
    }


def write_csv(
        path: Path,
        rows: list[dict[str, Any]],
) -> None:
    fieldnames = [
        "category",
        "order_key",
        "order_created_at",
        "customer_name",
        "customer_phone",
        "product_key",
        "product_name",
        "quantity",
        "order_amount",
        "payment_key",
        "payment_status",
        "payment_method",
        "requested_at",
        "approved_at",
        "latest_canceled_at",
        "cancel_amount",
        "balance_amount",
        "receipt_url",
        "has_payment",
    ]

    with path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(
        path: Path,
        data: Any,
) -> None:
    with path.open(
            "w",
            encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def print_summary(
        *,
        all_order_count: int,
        rows: list[dict[str, Any]],
) -> None:
    status_counter = Counter(
        row["payment_status"] or "UNPAID"
        for row in rows
    )

    category_counter = Counter(
        row["category"]
        for row in rows
    )

    print()
    print("=" * 60)
    print(f"Toss 전체 주문 수: {all_order_count}")
    print(f"DAKS 대상 주문 수: {len(rows)}")
    print()

    print("[상품별]")
    for category, count in sorted(
            category_counter.items()
    ):
        print(f"  {category}: {count}")

    print()
    print("[현재 결제 상태별]")
    for status, count in sorted(
            status_counter.items()
    ):
        print(f"  {status}: {count}")

    ever_paid_count = sum(
        1
        for row in rows
        if row["payment_status"]
        in {
            "DONE",
            "CANCELED",
            "PARTIAL_CANCELED",
        }
    )

    currently_valid_count = sum(
        1
        for row in rows
        if row["payment_status"]
        in {
            "DONE",
            "PARTIAL_CANCELED",
        }
    )

    canceled_count = sum(
        1
        for row in rows
        if row["payment_status"] == "CANCELED"
    )

    print()
    print("[결제 집계]")
    print(
        "  한 번이라도 승인된 주문: "
        f"{ever_paid_count}"
    )
    print(
        "  현재 유효 결제 주문: "
        f"{currently_valid_count}"
    )
    print(
        "  전액 취소 주문: "
        f"{canceled_count}"
    )


def main() -> None:
    args = parse_args()

    if args.limit < 1 or args.limit > 100:
        print(
            "--limit은 1~100 사이여야 합니다.",
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

    output_dir = Path(args.output_dir)
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        all_orders = fetch_all_orders(
            secret_key=secret_key,
            limit=args.limit,
            delay=args.delay,
            max_pages=args.max_pages,
        )
    except RuntimeError as exc:
        print(
            f"조회 실패: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    daks_orders = [
        order
        for order in all_orders
        if is_daks_order(order)
    ]

    normalized_rows = [
        normalize_order(order)
        for order in daks_orders
    ]

    if not args.include_unpaid:
        normalized_rows = [
            row
            for row in normalized_rows
            if row["has_payment"]
        ]

    normalized_rows.sort(
        key=lambda row: (
                row["approved_at"]
                or row["order_created_at"]
                or ""
        )
    )

    raw_json_path = (
            output_dir
            / "daks_linkpay_orders_raw.json"
    )

    csv_path = (
            output_dir
            / "daks_linkpay_orders.csv"
    )

    summary_json_path = (
            output_dir
            / "daks_linkpay_orders_summary.json"
    )

    write_json(
        raw_json_path,
        daks_orders,
    )

    write_csv(
        csv_path,
        normalized_rows,
    )

    summary = {
        "all_order_count": len(all_orders),
        "daks_order_count": len(normalized_rows),
        "category_counts": dict(
            Counter(
                row["category"]
                for row in normalized_rows
            )
        ),
        "status_counts": dict(
            Counter(
                row["payment_status"] or "UNPAID"
                for row in normalized_rows
            )
        ),
    }

    write_json(
        summary_json_path,
        summary,
    )

    print_summary(
        all_order_count=len(all_orders),
        rows=normalized_rows,
    )

    print()
    print(f"CSV 저장: {csv_path}")
    print(f"원본 JSON 저장: {raw_json_path}")
    print(
        f"요약 JSON 저장: {summary_json_path}"
    )


if __name__ == "__main__":
    main()