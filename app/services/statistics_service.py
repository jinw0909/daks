# app/services/statistics_service.py

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.db.models import Sponsor
from app.services.webhook_admin_service import (
    WebhookTransaction,
    build_webhook_transactions,
)


KST = ZoneInfo("Asia/Seoul")

TICKET_UNIT_PRICE = 19_900

DONE_STATUS = "DONE"

FULL_CANCELED_STATUSES = {
    "CANCELED",
    "CANCELD",
}

PARTIAL_CANCELED_STATUS = "PARTIAL_CANCELED"

FAILED_STATUSES = {
    "ABORTED",
    "EXPIRED",
}


@dataclass
class StatisticsPeriod:
    received_from: datetime | None = None
    received_to: datetime | None = None


@dataclass
class StatisticsSummary:
    total_transaction_count: int = 0

    valid_transaction_count: int = 0
    valid_amount: int = 0

    canceled_count: int = 0
    canceled_amount: int = 0

    partial_canceled_count: int = 0
    partial_canceled_amount: int = 0

    failed_count: int = 0

    ticket_quantity: int = 0
    invalid_ticket_amount_count: int = 0


@dataclass
class SourceStatistics:
    source_type: str
    source_label: str

    valid_transaction_count: int = 0
    valid_amount: int = 0

    canceled_count: int = 0
    canceled_amount: int = 0

    partial_canceled_count: int = 0
    partial_canceled_amount: int = 0

    failed_count: int = 0

    ticket_quantity: int = 0


@dataclass
class DailyStatistics:
    date: date

    valid_transaction_count: int = 0
    valid_amount: int = 0

    canceled_count: int = 0
    canceled_amount: int = 0

    partial_canceled_count: int = 0
    partial_canceled_amount: int = 0

    failed_count: int = 0

    ticket_quantity: int = 0


@dataclass
class TicketIssueStatistics:
    payment_id_missing: int = 0
    payment_not_found: int = 0
    duplicate_payment: int = 0
    payment_key_mismatch: int = 0

    @property
    def total(self) -> int:
        return (
                self.payment_id_missing
                + self.payment_not_found
                + self.duplicate_payment
                + self.payment_key_mismatch
        )


@dataclass
class PaginatedTransactions:
    items: list[WebhookTransaction]
    total_count: int
    current_page: int
    total_pages: int
    page_size: int


@dataclass
class TicketStatistics:
    summary: StatisticsSummary
    issue_summary: TicketIssueStatistics
    daily_statistics: list[DailyStatistics]
    transactions: PaginatedTransactions


@dataclass
class SponsorStatisticsItem:
    sponsor_id: int
    sponsor_name: str
    category: int | None
    product_key: str
    product_link: str | None
    is_active: bool

    valid_transaction_count: int = 0
    valid_amount: int = 0

    canceled_count: int = 0
    canceled_amount: int = 0

    partial_canceled_count: int = 0
    partial_canceled_amount: int = 0

    failed_count: int = 0

    latest_transaction_at: datetime | None = None


@dataclass
class SponsorStatistics:
    connected_sponsor_count: int

    valid_transaction_count: int
    valid_amount: int

    canceled_count: int
    canceled_amount: int

    partial_canceled_count: int
    partial_canceled_amount: int

    failed_count: int

    sponsors: list[SponsorStatisticsItem]

    selected_sponsor: SponsorStatisticsItem | None
    selected_transactions: PaginatedTransactions


@dataclass
class OverviewStatistics:
    summary: StatisticsSummary

    ticket: SourceStatistics
    sponsor: SourceStatistics
    unknown: SourceStatistics

    daily_statistics: list[DailyStatistics]
    recent_transactions: list[WebhookTransaction]


@dataclass
class AdminStatistics:
    period: StatisticsPeriod

    overview: OverviewStatistics
    tickets: TicketStatistics
    sponsors: SponsorStatistics


def normalize_datetime(
        value: datetime | None,
) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None:
        return value

    return (
        value.astimezone(KST)
        .replace(tzinfo=None)
    )


def parse_datetime_filter(
        value: str | None,
        *,
        is_end: bool = False,
) -> datetime | None:
    if not value:
        return None

    normalized = value.strip()

    if not normalized:
        return None

    try:
        parsed = datetime.fromisoformat(
            normalized
        )
    except ValueError:
        return None

    parsed = normalize_datetime(parsed)

    # datetime-local 값이 분 단위인 경우,
    # 종료 시각은 해당 분의 마지막까지 포함한다.
    if (
            is_end
            and len(normalized) == 16
    ):
        parsed = parsed.replace(
            second=59,
            microsecond=999999,
        )

    return parsed


def build_statistics_period(
        *,
        received_from: str | None = None,
        received_to: str | None = None,
) -> StatisticsPeriod:
    return StatisticsPeriod(
        received_from=parse_datetime_filter(
            received_from,
        ),
        received_to=parse_datetime_filter(
            received_to,
            is_end=True,
        ),
    )


def get_transaction_datetime(
        transaction: WebhookTransaction,
) -> datetime | None:
    return normalize_datetime(
        transaction.last_received_at
    )


def filter_transactions_by_period(
        transactions: list[WebhookTransaction],
        *,
        period: StatisticsPeriod,
) -> list[WebhookTransaction]:
    filtered: list[WebhookTransaction] = []

    for transaction in transactions:
        transaction_datetime = (
            get_transaction_datetime(
                transaction
            )
        )

        if (
                period.received_from
                and (
                transaction_datetime is None
                or transaction_datetime
                < period.received_from
        )
        ):
            continue

        if (
                period.received_to
                and (
                transaction_datetime is None
                or transaction_datetime
                > period.received_to
        )
        ):
            continue

        filtered.append(transaction)

    return filtered


def calculate_ticket_quantity(
        amount: int | None,
) -> tuple[int, bool]:
    if amount is None or amount <= 0:
        return 0, False

    if amount % TICKET_UNIT_PRICE != 0:
        return 0, True

    return (
        amount // TICKET_UNIT_PRICE,
        False,
    )


def add_transaction_to_summary(
        summary: StatisticsSummary,
        transaction: WebhookTransaction,
        *,
        include_ticket_quantity: bool = False,
) -> None:
    summary.total_transaction_count += 1

    amount = transaction.amount or 0
    status = transaction.status

    if status == DONE_STATUS:
        summary.valid_transaction_count += 1
        summary.valid_amount += amount

        if (
                include_ticket_quantity
                and transaction.source_type
                == "TICKET"
        ):
            quantity, invalid = (
                calculate_ticket_quantity(
                    transaction.amount
                )
            )

            summary.ticket_quantity += quantity

            if invalid:
                summary.invalid_ticket_amount_count += 1

    elif status in FULL_CANCELED_STATUSES:
        summary.canceled_count += 1
        summary.canceled_amount += amount

    elif status == PARTIAL_CANCELED_STATUS:
        summary.partial_canceled_count += 1
        summary.partial_canceled_amount += amount

    elif status in FAILED_STATUSES:
        summary.failed_count += 1


def build_summary(
        transactions: list[WebhookTransaction],
        *,
        include_ticket_quantity: bool = False,
) -> StatisticsSummary:
    summary = StatisticsSummary()

    for transaction in transactions:
        add_transaction_to_summary(
            summary,
            transaction,
            include_ticket_quantity=(
                include_ticket_quantity
            ),
        )

    return summary


def build_source_statistics(
        transactions: list[WebhookTransaction],
        *,
        source_type: str,
        source_label: str,
) -> SourceStatistics:
    statistics = SourceStatistics(
        source_type=source_type,
        source_label=source_label,
    )

    for transaction in transactions:
        if transaction.source_type != source_type:
            continue

        amount = transaction.amount or 0
        status = transaction.status

        if status == DONE_STATUS:
            statistics.valid_transaction_count += 1
            statistics.valid_amount += amount

            if source_type == "TICKET":
                quantity, _ = (
                    calculate_ticket_quantity(
                        transaction.amount
                    )
                )

                statistics.ticket_quantity += quantity

        elif status in FULL_CANCELED_STATUSES:
            statistics.canceled_count += 1
            statistics.canceled_amount += amount

        elif status == PARTIAL_CANCELED_STATUS:
            statistics.partial_canceled_count += 1
            statistics.partial_canceled_amount += amount

        elif status in FAILED_STATUSES:
            statistics.failed_count += 1

    return statistics


def build_daily_statistics(
        transactions: list[WebhookTransaction],
        *,
        include_ticket_quantity: bool = False,
) -> list[DailyStatistics]:
    grouped: dict[date, DailyStatistics] = {}

    for transaction in transactions:
        transaction_datetime = (
            get_transaction_datetime(
                transaction
            )
        )

        if transaction_datetime is None:
            continue

        transaction_date = (
            transaction_datetime.date()
        )

        daily = grouped.get(
            transaction_date
        )

        if daily is None:
            daily = DailyStatistics(
                date=transaction_date,
            )
            grouped[
                transaction_date
            ] = daily

        amount = transaction.amount or 0
        status = transaction.status

        if status == DONE_STATUS:
            daily.valid_transaction_count += 1
            daily.valid_amount += amount

            if (
                    include_ticket_quantity
                    and transaction.source_type
                    == "TICKET"
            ):
                quantity, _ = (
                    calculate_ticket_quantity(
                        transaction.amount
                    )
                )

                daily.ticket_quantity += quantity

        elif status in FULL_CANCELED_STATUSES:
            daily.canceled_count += 1
            daily.canceled_amount += amount

        elif status == PARTIAL_CANCELED_STATUS:
            daily.partial_canceled_count += 1
            daily.partial_canceled_amount += amount

        elif status in FAILED_STATUSES:
            daily.failed_count += 1

    return sorted(
        grouped.values(),
        key=lambda item: item.date,
        reverse=True,
    )


def build_ticket_issue_statistics(
        transactions: list[WebhookTransaction],
) -> TicketIssueStatistics:
    statistics = TicketIssueStatistics()

    for transaction in transactions:
        if transaction.source_type != "TICKET":
            continue

        if (
                transaction.issue_code
                == "PAYMENT_ID_MISSING"
        ):
            statistics.payment_id_missing += 1

        elif (
                transaction.issue_code
                == "PAYMENT_NOT_FOUND"
        ):
            statistics.payment_not_found += 1

        elif (
                transaction.issue_code
                == "DUPLICATE_PAYMENT"
        ):
            statistics.duplicate_payment += 1

        elif (
                transaction.issue_code
                == "PAYMENT_KEY_MISMATCH"
        ):
            statistics.payment_key_mismatch += 1

    return statistics


def paginate_transactions(
        transactions: list[WebhookTransaction],
        *,
        page: int,
        page_size: int,
) -> PaginatedTransactions:
    safe_page = max(page, 1)
    safe_page_size = max(page_size, 1)

    total_count = len(transactions)
    total_pages = max(
        1,
        (
                total_count
                + safe_page_size
                - 1
        ) // safe_page_size,
        )

    if safe_page > total_pages:
        safe_page = total_pages

    start = (
                    safe_page - 1
            ) * safe_page_size
    end = start + safe_page_size

    return PaginatedTransactions(
        items=transactions[start:end],
        total_count=total_count,
        current_page=safe_page,
        total_pages=total_pages,
        page_size=safe_page_size,
    )


def build_ticket_statistics(
        transactions: list[WebhookTransaction],
        *,
        page: int = 1,
        page_size: int = 20,
) -> TicketStatistics:
    ticket_transactions = [
        transaction
        for transaction in transactions
        if transaction.source_type == "TICKET"
    ]

    return TicketStatistics(
        summary=build_summary(
            ticket_transactions,
            include_ticket_quantity=True,
        ),
        issue_summary=(
            build_ticket_issue_statistics(
                ticket_transactions
            )
        ),
        daily_statistics=(
            build_daily_statistics(
                ticket_transactions,
                include_ticket_quantity=True,
            )
        ),
        transactions=paginate_transactions(
            ticket_transactions,
            page=page,
            page_size=page_size,
        ),
    )


def get_connected_sponsors(
        db: Session,
) -> list[Sponsor]:
    sponsors = (
        db.query(Sponsor)
        .filter(
            Sponsor.toss_product_key.isnot(
                None
            ),
            Sponsor.toss_product_key != "",
            )
        .order_by(
            Sponsor.display_order.asc(),
            Sponsor.id.asc(),
        )
        .all()
    )

    return [
        sponsor
        for sponsor in sponsors
        if (
                sponsor.toss_product_key
                and sponsor.toss_product_key.strip()
        )
    ]


def build_sponsor_statistics(
        db: Session,
        transactions: list[WebhookTransaction],
        *,
        selected_sponsor_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
) -> SponsorStatistics:
    sponsors = get_connected_sponsors(db)

    sponsor_transactions: dict[
        int,
        list[WebhookTransaction],
    ] = defaultdict(list)

    for transaction in transactions:
        if (
                transaction.source_type
                == "SPONSOR"
                and transaction.sponsor_id
                is not None
        ):
            sponsor_transactions[
                transaction.sponsor_id
            ].append(transaction)

    sponsor_items: list[
        SponsorStatisticsItem
    ] = []

    total_valid_count = 0
    total_valid_amount = 0

    total_canceled_count = 0
    total_canceled_amount = 0

    total_partial_canceled_count = 0
    total_partial_canceled_amount = 0

    total_failed_count = 0

    for sponsor in sponsors:
        product_key = (
            sponsor.toss_product_key.strip()
        )

        item = SponsorStatisticsItem(
            sponsor_id=sponsor.id,
            sponsor_name=sponsor.name,
            category=getattr(
                sponsor,
                "category",
                None,
            ),
            product_key=product_key,
            product_link=getattr(
                sponsor,
                "toss_product_link",
                None,
            ),
            is_active=bool(
                getattr(
                    sponsor,
                    "is_active",
                    False,
                )
            ),
        )

        items = sponsor_transactions.get(
            sponsor.id,
            [],
        )

        for transaction in items:
            amount = transaction.amount or 0
            status = transaction.status

            transaction_datetime = (
                get_transaction_datetime(
                    transaction
                )
            )

            if (
                    transaction_datetime
                    and (
                    item.latest_transaction_at
                    is None
                    or transaction_datetime
                    > item.latest_transaction_at
            )
            ):
                item.latest_transaction_at = (
                    transaction_datetime
                )

            if status == DONE_STATUS:
                item.valid_transaction_count += 1
                item.valid_amount += amount

            elif status in FULL_CANCELED_STATUSES:
                item.canceled_count += 1
                item.canceled_amount += amount

            elif status == PARTIAL_CANCELED_STATUS:
                item.partial_canceled_count += 1
                item.partial_canceled_amount += amount

            elif status in FAILED_STATUSES:
                item.failed_count += 1

        total_valid_count += (
            item.valid_transaction_count
        )
        total_valid_amount += item.valid_amount

        total_canceled_count += (
            item.canceled_count
        )
        total_canceled_amount += (
            item.canceled_amount
        )

        total_partial_canceled_count += (
            item.partial_canceled_count
        )
        total_partial_canceled_amount += (
            item.partial_canceled_amount
        )

        total_failed_count += (
            item.failed_count
        )

        sponsor_items.append(item)

    sponsor_items.sort(
        key=lambda item: (
            item.valid_amount,
            item.valid_transaction_count,
            item.latest_transaction_at
            or datetime.min,
        ),
        reverse=True,
    )

    selected_sponsor = next(
        (
            item
            for item in sponsor_items
            if (
                selected_sponsor_id
                is not None
                and item.sponsor_id
                == selected_sponsor_id
        )
        ),
        None,
    )

    selected_transaction_items: list[
        WebhookTransaction
    ] = []

    if selected_sponsor is not None:
        selected_transaction_items = sorted(
            sponsor_transactions.get(
                selected_sponsor.sponsor_id,
                [],
            ),
            key=lambda transaction: (
                    get_transaction_datetime(
                        transaction
                    )
                    or datetime.min
            ),
            reverse=True,
        )

    selected_transactions = (
        paginate_transactions(
            selected_transaction_items,
            page=page,
            page_size=page_size,
        )
    )

    return SponsorStatistics(
        connected_sponsor_count=len(
            sponsor_items
        ),
        valid_transaction_count=(
            total_valid_count
        ),
        valid_amount=total_valid_amount,
        canceled_count=(
            total_canceled_count
        ),
        canceled_amount=(
            total_canceled_amount
        ),
        partial_canceled_count=(
            total_partial_canceled_count
        ),
        partial_canceled_amount=(
            total_partial_canceled_amount
        ),
        failed_count=total_failed_count,
        sponsors=sponsor_items,
        selected_sponsor=selected_sponsor,
        selected_transactions=selected_transactions,
    )


def build_overview_statistics(
        transactions: list[WebhookTransaction],
) -> OverviewStatistics:
    ticket_statistics = (
        build_source_statistics(
            transactions,
            source_type="TICKET",
            source_label="일반 티켓",
        )
    )

    sponsor_statistics = (
        build_source_statistics(
            transactions,
            source_type="SPONSOR",
            source_label="스폰서",
        )
    )

    unknown_statistics = (
        build_source_statistics(
            transactions,
            source_type="UNKNOWN",
            source_label="미등록 상품",
        )
    )

    return OverviewStatistics(
        summary=build_summary(
            transactions,
            include_ticket_quantity=True,
        ),
        ticket=ticket_statistics,
        sponsor=sponsor_statistics,
        unknown=unknown_statistics,
        daily_statistics=(
            build_daily_statistics(
                transactions,
                include_ticket_quantity=True,
            )
        ),
        recent_transactions=transactions[:10],
    )


def build_admin_statistics(
        db: Session,
        *,
        ticket_product_key: str,
        received_from: str | None = None,
        received_to: str | None = None,
        sponsor_id: int | None = None,
        ticket_page: int = 1,
        sponsor_page: int = 1,
        page_size: int = 20,
) -> AdminStatistics:
    period = build_statistics_period(
        received_from=received_from,
        received_to=received_to,
    )

    transactions = build_webhook_transactions(
        db,
        ticket_product_key=(
            ticket_product_key.strip()
        ),
    )

    filtered_transactions = (
        filter_transactions_by_period(
            transactions,
            period=period,
        )
    )

    return AdminStatistics(
        period=period,
        overview=build_overview_statistics(
            filtered_transactions
        ),
        tickets=build_ticket_statistics(
            filtered_transactions,
            page=ticket_page,
            page_size=page_size,
        ),
        sponsors=build_sponsor_statistics(
            db,
            filtered_transactions,
            selected_sponsor_id=sponsor_id,
            page=sponsor_page,
            page_size=page_size,
        ),
    )


def get_quick_period_values(
        period_type: str | None,
) -> tuple[str, str]:
    now = datetime.now(KST).replace(
        tzinfo=None
    )

    if period_type == "today":
        start = datetime.combine(
            now.date(),
            time.min,
        )

    elif period_type == "7days":
        start = datetime.combine(
            now.date() - timedelta(days=6),
            time.min,
            )

    elif period_type == "30days":
        start = datetime.combine(
            now.date() - timedelta(days=29),
            time.min,
            )

    else:
        return "", ""

    end = datetime.combine(
        now.date(),
        time.max,
    )

    return (
        start.strftime("%Y-%m-%dT%H:%M"),
        end.strftime("%Y-%m-%dT%H:%M"),
    )