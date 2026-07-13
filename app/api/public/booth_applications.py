from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.schemas.booth_application import (
    BoothApplicationCreateRequest,
    BoothApplicationCreateResponse,
)
from app.services.booth_application_service import (
    submit_booth_application,
)


router = APIRouter(
    prefix="/booth-applications",
    tags=["부스 신청"],
)


@router.post(
    "",
    response_model=BoothApplicationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_booth_application(
        request: BoothApplicationCreateRequest,
        db: DbSession,
):
    return submit_booth_application(
        db,
        request,
    )