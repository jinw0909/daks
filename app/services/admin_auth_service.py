from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_admin_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.db.models.admin import Admin
from app.repositories.admin_repository import (
    create_admin_refresh_token,
    find_admin_by_id,
    find_admin_by_username,
    find_admin_refresh_token,
    revoke_admin_refresh_token,
)


@dataclass
class AdminLoginResult:
    admin: Admin
    access_token: str
    refresh_token: str


def login_admin(
        db: Session,
        *,
        username: str,
        password: str,
) -> AdminLoginResult:
    admin = find_admin_by_username(
        db,
        username,
    )

    if not admin or not verify_password(
            password,
            admin.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=403,
            detail="비활성화된 관리자 계정입니다.",
        )

    access_token = create_admin_access_token(admin.id)
    refresh_token = create_refresh_token()

    try:
        create_admin_refresh_token(
            db,
            admin_id=admin.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(timezone.utc).replace(
                tzinfo=None,
            )
                       + timedelta(
                days=settings.admin_refresh_token_expire_days,
            ),
        )

        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise

    return AdminLoginResult(
        admin=admin,
        access_token=access_token,
        refresh_token=refresh_token,
    )


def refresh_admin_access_token(
        db: Session,
        raw_refresh_token: str,
) -> str:
    token_hash = hash_refresh_token(raw_refresh_token)

    stored_token = find_admin_refresh_token(
        db,
        token_hash,
    )

    if not stored_token:
        raise HTTPException(
            status_code=401,
            detail="유효하지 않은 리프레시 토큰입니다.",
        )

    if stored_token.revoked_at is not None:
        raise HTTPException(
            status_code=401,
            detail="폐기된 리프레시 토큰입니다.",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if stored_token.expires_at <= now:
        raise HTTPException(
            status_code=401,
            detail="리프레시 토큰이 만료되었습니다.",
        )

    admin = find_admin_by_id(
        db,
        stored_token.admin_id,
    )

    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=401,
            detail="관리자 계정을 사용할 수 없습니다.",
        )

    return create_admin_access_token(admin.id)


def logout_admin(
        db: Session,
        raw_refresh_token: str | None,
) -> None:
    if not raw_refresh_token:
        return

    try:
        revoke_admin_refresh_token(
            db,
            hash_refresh_token(raw_refresh_token),
            datetime.now(timezone.utc).replace(tzinfo=None),
        )

        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise