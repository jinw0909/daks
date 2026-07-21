from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.db.models import (
    Payment,
    Sponsor,
    WebhookLogHistory,
)


TOSS_FINAL_STATUSES = {
    "DONE",
    "CANCELED",
    "ABORTED",
    "EXPIRED",
    "PARTIAL_CANCELED",
}


@dataclass
class WebhookTransaction:
    payment_key: str

    order_id: str | None = None
    product_key: str | None = None
    product_name: str | None = None

    payment_id: int | None = None
    ticket_user_id: int | None = None

    status: str | None = None
    amount: int | None = None
    method: str | None = None
    customer_name: str | None = None

    approved_at: str | None = None
    created_at: str | None = None
    last_received_at: datetime | None = None

    event_count: int = 0
    history_ids: list[int] = field(
        default_factory=list
    )

    source_type: str = "UNKNOWN"
    source_label: str = "미등록 상품"

    sponsor_id: int | None = None
    sponsor_name: str | None = None

    payment_exists: bool = False
    payment_status: int | None = None
    payment_toss_key: str | None = None

    issue_code: str | None = None
    issue_label: str | None = None

    duplicate_payment: bool = False


def to_optional_int(
        value,
) -> int | None:
    if value is None:
        return None

    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def to_amount_int(
        value,
) -> int | None:
    if value is None:
        return None

    normalized = str(value).strip()

    if not normalized:
        return None

    try:
        return int(
            Decimal(normalized)
        )
    except (
            InvalidOperation,
            TypeError,
            ValueError,
    ):
        return None


def normalize_keyword(
        value: str | None,
) -> str:
    return (
        value.strip().lower()
        if value
        else ""
    )

def parse_datetime_filter(
        value: str | None,
) -> datetime | None:
    if not value:
        return None

    normalized = value.strip()

    if not normalized:
        return None

    try:
        return datetime.fromisoformat(
            normalized
        )
    except ValueError:
        return None


def normalize_comparable_datetime(
        value: datetime | None,
) -> datetime | None:
    if value is None:
        return None

    # DB datetime이 timezone-aware로 반환되더라도
    # datetime-local 입력값과 비교할 수 있도록 맞춘다.
    return value.replace(
        tzinfo=None
    )


def build_webhook_transactions(
        db: Session,
        *,
        ticket_product_key: str,
) -> list[WebhookTransaction]:
    histories = (
        db.query(WebhookLogHistory)
        .filter(
            WebhookLogHistory.payment_key.isnot(None),
            WebhookLogHistory.eventType
            == "ORDER_PAYMENT_STATUS_CHANGED",
            )
        .order_by(
            WebhookLogHistory.payment_key.asc(),
            WebhookLogHistory.datetime.asc(),
            WebhookLogHistory.id.asc(),
        )
        .all()
    )

    sponsors = (
        db.query(Sponsor)
        .filter(
            Sponsor.toss_product_key.isnot(None)
        )
        .all()
    )

    sponsor_by_product_key = {
        sponsor.toss_product_key: sponsor
        for sponsor in sponsors
        if sponsor.toss_product_key
    }

    grouped: dict[
        str,
        WebhookTransaction,
    ] = {}

    for history in histories:
        payment_key = (
            history.payment_key.strip()
            if history.payment_key
            else ""
        )

        if not payment_key:
            continue

        transaction = grouped.get(
            payment_key
        )

        if transaction is None:
            transaction = WebhookTransaction(
                payment_key=payment_key,
            )
            grouped[payment_key] = transaction

        transaction.event_count += 1
        transaction.history_ids.append(
            history.id
        )

        # NULL 값으로 기존 정보를 덮어쓰지 않는다.
        if history.order_id:
            transaction.order_id = (
                history.order_id
            )

        if history.product_key:
            transaction.product_key = (
                history.product_key
            )

        if history.product_name:
            transaction.product_name = (
                history.product_name
            )

        parsed_payment_id = to_optional_int(
            history.enrollmentid
        )

        if parsed_payment_id is not None:
            transaction.payment_id = (
                parsed_payment_id
            )

        parsed_ticket_user_id = (
            to_optional_int(
                history.ticketuser_id
            )
        )

        if (
                parsed_ticket_user_id
                is not None
        ):
            transaction.ticket_user_id = (
                parsed_ticket_user_id
            )

        # ERROR는 Toss 결제 상태가 아니라
        # 웹훅 처리 중 내부 오류 표시이므로
        # 거래 최종 상태 계산에서 제외한다.
        if (
                history.status
                and history.status != "ERROR"
        ):
            transaction.status = (
                history.status
            )

        parsed_amount = to_amount_int(
            history.amount
        )

        if parsed_amount is not None:
            transaction.amount = (
                parsed_amount
            )

        if history.method:
            transaction.method = (
                history.method
            )

        if history.name:
            transaction.customer_name = (
                history.name
            )

        if history.approved_at:
            transaction.approved_at = (
                history.approved_at
            )

        if history.created_at:
            transaction.created_at = (
                history.created_at
            )

        if history.datetime:
            transaction.last_received_at = (
                history.datetime
            )

    payment_ids = {
        transaction.payment_id
        for transaction in grouped.values()
        if transaction.payment_id
           is not None
    }

    payments = []

    if payment_ids:
        payments = (
            db.query(Payment)
            .filter(
                Payment.id.in_(payment_ids)
            )
            .all()
        )

    payment_by_id = {
        payment.id: payment
        for payment in payments
    }

    transactions = list(
        grouped.values()
    )

    # 먼저 출처와 내부 Payment 연결 상태를 계산한다.
    for transaction in transactions:
        sponsor = sponsor_by_product_key.get(
            transaction.product_key
        )

        normalized_product_key = (
            transaction.product_key.strip()
            if transaction.product_key
            else ""
        )

        normalized_ticket_product_key = (
            ticket_product_key.strip()
            if ticket_product_key
            else ""
        )

        if (
                normalized_product_key
                and normalized_product_key
                == normalized_ticket_product_key
        ):
            transaction.source_type = "TICKET"
            transaction.source_label = "일반 티켓"

        elif sponsor:
            transaction.source_type = (
                "SPONSOR"
            )
            transaction.source_label = (
                sponsor.name
            )
            transaction.sponsor_id = (
                sponsor.id
            )
            transaction.sponsor_name = (
                sponsor.name
            )

        else:
            transaction.source_type = (
                "UNKNOWN"
            )
            transaction.source_label = (
                    transaction.product_name
                    or "미등록 상품"
            )

        if transaction.payment_id:
            payment = payment_by_id.get(
                transaction.payment_id
            )

            if payment:
                transaction.payment_exists = (
                    True
                )
                transaction.payment_status = (
                    payment.status
                )
                transaction.payment_toss_key = (
                    payment.toss_payment_key
                )

    # 일반 티켓 중복 결제 판정:
    # 동일 paymentId에 최종 DONE인 서로 다른
    # paymentKey가 2개 이상인 경우
    active_done_by_payment_id: dict[
        int,
        list[WebhookTransaction],
    ] = defaultdict(list)

    for transaction in transactions:
        if (
                transaction.source_type
                == "TICKET"
                and transaction.payment_id
                is not None
                and transaction.status == "DONE"
        ):
            active_done_by_payment_id[
                transaction.payment_id
            ].append(transaction)

    duplicate_payment_ids = {
        payment_id
        for payment_id, items
        in active_done_by_payment_id.items()
        if len(
            {
                item.payment_key
                for item in items
            }
        ) > 1
    }

    for transaction in transactions:
        if (
                transaction.source_type
                == "TICKET"
        ):
            if transaction.payment_id is None:
                transaction.issue_code = (
                    "PAYMENT_ID_MISSING"
                )
                transaction.issue_label = (
                    "Payment ID 누락"
                )

            elif not transaction.payment_exists:
                transaction.issue_code = (
                    "PAYMENT_NOT_FOUND"
                )
                transaction.issue_label = (
                    "Payment 조회 실패"
                )

            elif (
                    transaction.payment_id
                    in duplicate_payment_ids
                    and transaction.status
                    == "DONE"
            ):
                transaction.duplicate_payment = (
                    True
                )
                transaction.issue_code = (
                    "DUPLICATE_PAYMENT"
                )
                transaction.issue_label = (
                    "중복 결제"
                )

            elif (
                    transaction.status == "DONE"
                    and
                    transaction.payment_toss_key
                    and
                    transaction.payment_toss_key
                    != transaction.payment_key
            ):
                transaction.issue_code = (
                    "PAYMENT_KEY_MISMATCH"
                )
                transaction.issue_label = (
                    "Payment Key 불일치"
                )

    return sorted(
        transactions,
        key=lambda item: (
            item.last_received_at
            or datetime.min,
            item.payment_key,
        ),
        reverse=True,
    )


def filter_webhook_transactions(
        transactions: list[
            WebhookTransaction
        ],
        *,
        keyword: str | None = None,
        source: str | None = None,
        status: str | None = None,
        issue: str | None = None,
        received_from: str | None = None,
        received_to: str | None = None,
) -> list[WebhookTransaction]:
    normalized_keyword = normalize_keyword(
        keyword
    )

    parsed_received_from = (
        parse_datetime_filter(
            received_from
        )
    )

    parsed_received_to = (
        parse_datetime_filter(
            received_to
        )
    )

    filtered = []

    for transaction in transactions:

        transaction_received_at = (
            normalize_comparable_datetime(
                transaction.last_received_at
            )
        )

        if parsed_received_from:
            if (
                    transaction_received_at
                    is None
                    or transaction_received_at
                    < parsed_received_from
            ):
                continue

        if parsed_received_to:
            if (
                    transaction_received_at
                    is None
                    or transaction_received_at
                    > parsed_received_to
            ):
                continue

        if normalized_keyword:
            searchable_values = [
                transaction.payment_key,
                transaction.order_id,
                transaction.product_key,
                transaction.product_name,
                transaction.customer_name,
                transaction.sponsor_name,
                (
                    str(transaction.payment_id)
                    if transaction.payment_id
                       is not None
                    else None
                ),
            ]

            if not any(
                    normalized_keyword
                    in str(value).lower()
                    for value in searchable_values
                    if value
            ):
                continue

        if (
                source
                and transaction.source_type
                != source
        ):
            continue

        if (
                status
                and transaction.status
                != status
        ):
            continue

        if issue == "NORMAL":
            if transaction.issue_code:
                continue

        elif (
                issue
                and transaction.issue_code
                != issue
        ):
            continue

        filtered.append(transaction)

    return filtered


def paginate_items(
        items: list,
        *,
        page: int,
        page_size: int,
) -> tuple[list, int]:
    total_count = len(items)

    start = (page - 1) * page_size
    end = start + page_size

    return (
        items[start:end],
        total_count,
    )


def get_webhook_transaction(
        db: Session,
        *,
        payment_key: str,
        ticket_product_key: str,
) -> WebhookTransaction | None:
    transactions = build_webhook_transactions(
        db,
        ticket_product_key=(
            ticket_product_key
        ),
    )

    return next(
        (
            transaction
            for transaction in transactions
            if transaction.payment_key
               == payment_key
        ),
        None,
    )


def get_transaction_histories(
        db: Session,
        *,
        payment_key: str,
) -> list[WebhookLogHistory]:
    return (
        db.query(WebhookLogHistory)
        .filter(
            WebhookLogHistory.payment_key
            == payment_key
        )
        .order_by(
            WebhookLogHistory.datetime.asc(),
            WebhookLogHistory.id.asc(),
        )
        .all()
    )