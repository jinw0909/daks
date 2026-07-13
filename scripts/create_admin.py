from getpass import getpass

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.repositories.admin_repository import (
    create_admin,
    find_admin_by_username,
)


def main() -> None:
    username = input("관리자 아이디: ").strip()
    name = input("관리자 이름: ").strip()
    password = getpass("관리자 비밀번호: ")
    password_confirm = getpass("비밀번호 확인: ")

    if password != password_confirm:
        raise ValueError("비밀번호가 일치하지 않습니다.")

    if len(password) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다.")

    with SessionLocal() as db:
        if find_admin_by_username(db, username):
            raise ValueError("이미 존재하는 관리자 아이디입니다.")

        admin = create_admin(
            db,
            username=username,
            password_hash=hash_password(password),
            name=name,
        )

        db.commit()
        db.refresh(admin)

        print(f"관리자 생성 완료: {admin.username}")


if __name__ == "__main__":
    main()