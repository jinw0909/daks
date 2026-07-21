from sqlalchemy.orm import Session

from app.db.models.webhook_log import WebhookLog


def find_webhook_logs_by_payment_id(
        db: Session,
        *,
        payment_id: int,
) -> list[WebhookLog]:
    return (
        db.query(WebhookLog)
        .filter(
            WebhookLog.enrollmentid == str(payment_id),
            )
        .order_by(
            WebhookLog.datetime.desc(),
            WebhookLog.id.desc(),
        )
        .all()
    )