# app/services/s3_service.py

import logging
from uuid import uuid4

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)
from fastapi import (
    HTTPException,
    UploadFile,
)

from app.core.config import settings


logger = logging.getLogger(__name__)


ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def create_s3_client():
    client_kwargs = {
        "service_name": "s3",
        "region_name": settings.aws_region,
    }

    # 로컬 환경에서 AWS 키가 설정된 경우에만 직접 전달한다.
    # 운영 환경에서 IAM Role을 사용할 때는 키를 전달하지 않는다.
    if (
            settings.aws_access_key_id
            and settings.aws_secret_access_key
    ):
        client_kwargs.update(
            {
                "aws_access_key_id": (
                    settings.aws_access_key_id
                ),
                "aws_secret_access_key": (
                    settings.aws_secret_access_key
                ),
            }
        )

    return boto3.client(**client_kwargs)


s3_client = create_s3_client()


def normalize_public_base_url() -> str:
    return settings.s3_public_base_url.rstrip("/")


async def validate_image_file(
        file: UploadFile,
) -> tuple[bytes, str]:
    content_type = file.content_type or ""

    extension = ALLOWED_IMAGE_CONTENT_TYPES.get(
        content_type
    )

    if not extension:
        raise HTTPException(
            status_code=400,
            detail=(
                "JPG, PNG, WEBP 이미지만 "
                "업로드할 수 있습니다."
            ),
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="빈 파일은 업로드할 수 없습니다.",
        )

    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=(
                "이미지는 최대 5MB까지 "
                "업로드할 수 있습니다."
            ),
        )

    return content, extension


async def upload_speaker_profile_image(
        *,
        speaker_id: int,
        file: UploadFile,
) -> tuple[str, str]:
    content, extension = await validate_image_file(
        file
    )

    object_key = (
        f"{settings.s3_speaker_image_prefix}/"
        f"{speaker_id}/"
        f"{uuid4().hex}{extension}"
    )

    try:
        s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key,
            Body=content,
            ContentType=file.content_type,
            CacheControl=(
                "public, max-age=31536000, immutable"
            ),
        )

    except ClientError as exc:
        error = exc.response.get(
            "Error",
            {},
        )

        error_code = error.get(
            "Code",
            "Unknown",
        )

        error_message = error.get(
            "Message",
            str(exc),
        )

        logger.exception(
            (
                "S3 연사 프로필 이미지 업로드 실패: "
                "bucket=%s, key=%s, "
                "code=%s, message=%s"
            ),
            settings.s3_bucket_name,
            object_key,
            error_code,
            error_message,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                f"S3 업로드 실패: {error_code}"
            ),
        ) from exc

    except BotoCoreError as exc:
        logger.exception(
            (
                "AWS SDK 오류로 연사 프로필 이미지 "
                "업로드 실패: bucket=%s, key=%s"
            ),
            settings.s3_bucket_name,
            object_key,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "AWS 연결 또는 인증 설정에 "
                "문제가 있습니다."
            ),
        ) from exc

    public_url = (
        f"{normalize_public_base_url()}/"
        f"{object_key}"
    )

    return object_key, public_url


async def upload_sponsor_logo_image(
        *,
        sponsor_id: int,
        file: UploadFile,
) -> tuple[str, str]:
    content, extension = await validate_image_file(
        file
    )

    object_key = (
        f"{settings.s3_sponsor_logo_prefix}/"
        f"{sponsor_id}/"
        f"{uuid4().hex}{extension}"
    )

    try:
        s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key,
            Body=content,
            ContentType=file.content_type,
            CacheControl=(
                "public, max-age=31536000, immutable"
            ),
        )

    except ClientError as exc:
        error = exc.response.get(
            "Error",
            {},
        )

        error_code = error.get(
            "Code",
            "Unknown",
        )

        error_message = error.get(
            "Message",
            str(exc),
        )

        logger.exception(
            (
                "S3 스폰서 로고 이미지 업로드 실패: "
                "bucket=%s, key=%s, "
                "code=%s, message=%s"
            ),
            settings.s3_bucket_name,
            object_key,
            error_code,
            error_message,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                f"S3 업로드 실패: {error_code}"
            ),
        ) from exc

    except BotoCoreError as exc:
        logger.exception(
            (
                "AWS SDK 오류로 스폰서 로고 이미지 "
                "업로드 실패: bucket=%s, key=%s"
            ),
            settings.s3_bucket_name,
            object_key,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "AWS 연결 또는 인증 설정에 "
                "문제가 있습니다."
            ),
        ) from exc

    public_url = (
        f"{normalize_public_base_url()}/"
        f"{object_key}"
    )

    return object_key, public_url


def extract_object_key_from_public_url(
        public_url: str,
) -> str | None:
    if not public_url:
        return None

    base_url = normalize_public_base_url()
    prefix = f"{base_url}/"

    if not public_url.startswith(prefix):
        return None

    object_key = public_url.removeprefix(
        prefix
    )

    return object_key or None


def delete_s3_object(
        object_key: str,
) -> None:
    if not object_key:
        return

    try:
        s3_client.delete_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key,
        )

    except (BotoCoreError, ClientError):
        # 새 이미지와 DB 저장은 이미 완료됐는데
        # 이전 이미지 삭제만 실패한 경우이므로
        # 사용자 요청 전체를 실패시키지는 않는다.
        logger.exception(
            (
                "기존 S3 이미지 삭제 실패: "
                "bucket=%s, key=%s"
            ),
            settings.s3_bucket_name,
            object_key,
        )