# scripts/create_tables.py

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import engine


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("테이블 생성 완료")


if __name__ == "__main__":
    main()