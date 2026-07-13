from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models.admin import Admin
from app.db.models.admin_refresh_token import AdminRefreshToken


def find_admin_by_username(
        db: Session,
        username: str,
) -> Admin | None:
    stmt = select(Admin).where(
        Admin.username == username,
        )

    return db.scalar(stmt)


def find_admin_by_id(
        db: Session,
        admin_id: int,
) -> Admin | None:
    return db.get(Admin, admin_id)


def create_admin(
        db: Session,
        *,
        username: str,
        password_hash: str,
        name: str,
) -> Admin:
    admin = Admin(
        username=username,
        password_hash=password_hash,
        name=name,
        is_active=True,
    )

    db.add(admin)
    db.flush()

    return admin


def create_admin_refresh_token(
        db: Session,
        *,
        admin_id: int,
        token_hash: str,
        expires_at: datetime,
) -> AdminRefreshToken:
    refresh_token = AdminRefreshToken(
        admin_id=admin_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    db.add(refresh_token)
    db.flush()

    return refresh_token


def find_admin_refresh_token(
        db: Session,
        token_hash: str,
) -> AdminRefreshToken | None:
    stmt = select(AdminRefreshToken).where(
        AdminRefreshToken.token_hash == token_hash,
        )

    return db.scalar(stmt)


def revoke_admin_refresh_token(
        db: Session,
        token_hash: str,
        revoked_at: datetime,
) -> None:
    stmt = (
        update(AdminRefreshToken)
        .where(
            AdminRefreshToken.token_hash == token_hash,
            AdminRefreshToken.revoked_at.is_(None),
            )
        .values(revoked_at=revoked_at)
    )

    db.execute(stmt)