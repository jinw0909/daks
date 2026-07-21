from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models.sponsor import Sponsor


def find_sponsor_by_id(
        db: Session,
        sponsor_id: int,
) -> Sponsor | None:
    return (
        db.query(Sponsor)
        .filter(
            Sponsor.id == sponsor_id,
            )
        .first()
    )


def find_sponsor_by_product_key(
        db: Session,
        toss_product_key: str,
) -> Sponsor | None:
    return (
        db.query(Sponsor)
        .filter(
            Sponsor.toss_product_key == toss_product_key,
            )
        .first()
    )


def find_sponsors(
        db: Session,
        *,
        keyword: str | None = None,
        category: int | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
) -> list[Sponsor]:
    query = db.query(Sponsor)

    if keyword:
        normalized_keyword = keyword.strip()

        if normalized_keyword:
            like_keyword = f"%{normalized_keyword}%"

            query = query.filter(
                or_(
                    Sponsor.name.ilike(like_keyword),
                    Sponsor.toss_product_key.ilike(like_keyword),
                    Sponsor.website_url.ilike(like_keyword),
                )
            )

    if category is not None:
        query = query.filter(
            Sponsor.category == category,
            )

    if is_active is not None:
        query = query.filter(
            Sponsor.is_active == is_active,
            )

    return (
        query
        .order_by(
            Sponsor.category.asc(),
            Sponsor.display_order.asc(),
            Sponsor.id.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


def count_sponsors(
        db: Session,
        *,
        keyword: str | None = None,
        category: int | None = None,
        is_active: bool | None = None,
) -> int:
    query = db.query(
        func.count(Sponsor.id)
    )

    if keyword:
        normalized_keyword = keyword.strip()

        if normalized_keyword:
            like_keyword = f"%{normalized_keyword}%"

            query = query.filter(
                or_(
                    Sponsor.name.ilike(like_keyword),
                    Sponsor.toss_product_key.ilike(like_keyword),
                    Sponsor.website_url.ilike(like_keyword),
                )
            )

    if category is not None:
        query = query.filter(
            Sponsor.category == category,
            )

    if is_active is not None:
        query = query.filter(
            Sponsor.is_active == is_active,
            )

    return int(
        query.scalar() or 0
    )