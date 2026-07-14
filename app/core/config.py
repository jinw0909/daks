# app/core/config.py

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DAKS API"
    app_env: str = "local"
    debug: bool = False

    host: str = "127.0.0.1"
    port: int = 8000

    database_host: str = "127.0.0.1"
    database_port: int = 3306
    database_name: str
    database_user: str
    database_password: str

    database_echo: bool = False

    public_base_url: str = "http://127.0.0.1:8000"

    mail_host: str = "smtp.gmail.com"
    mail_port: int = 587
    mail_username: str = ""
    mail_password: str = ""
    mail_from_email: str = ""
    mail_from_name: str = "DAKS"

    admin_jwt_secret_key: str
    admin_jwt_algorithm: str = "HS256"

    admin_access_token_expire_minutes: int = 30
    admin_refresh_token_expire_days: int = 7

    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    aws_region: str = "ap-northeast-2"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    s3_bucket_name: str
    s3_public_base_url: str
    s3_speaker_image_prefix: str = "speakers"

    toss_ticket_product_link: str
    toss_ticket_product_key: str
    ticket_payment_name: str = "2026 Digital Asset Korea Summit Ticket"
    ticket_expected_amount: int = 19000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


    @property
    def database_url(self) -> str:
        encoded_user = quote_plus(self.database_user)
        encoded_password = quote_plus(self.database_password)

        return (
            f"mysql+pymysql://"
            f"{encoded_user}:{encoded_password}"
            f"@{self.database_host}:{self.database_port}"
            f"/{self.database_name}"
            f"?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()