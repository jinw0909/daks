from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import decode_admin_access_token
from app.db.models.admin import Admin
from app.repositories.admin_repository import find_admin_by_id


def resolve_admin_from_access_token(
        db: Session,
        access_token: str | None,
) -> Admin | None:
    if not access_token:
        return None

    admin_id = decode_admin_access_token(access_token)

    if admin_id is None:
        return None

    admin = find_admin_by_id(
        db,
        admin_id,
    )

    if not admin or not admin.is_active:
        return None

    return admin


def get_current_admin(
        admin_access_token: Annotated[
            str | None,
            Cookie(),
        ] = None,
        db: Session = Depends(get_db),
) -> Admin:
    admin = resolve_admin_from_access_token(
        db,
        admin_access_token,
    )

    if not admin:
        raise HTTPException(
            status_code=401,
            detail="관리자 로그인이 필요합니다.",
        )

    return admin


def get_optional_admin(
        admin_access_token: str | None = Cookie(default=None),
        db: Session = Depends(get_db),
) -> Admin | None:
    return resolve_admin_from_access_token(
        db,
        admin_access_token,
    )


CurrentAdmin = Annotated[
    Admin,
    Depends(get_current_admin),
]


