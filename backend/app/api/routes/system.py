from fastapi import APIRouter, status

from app.api.schemas.errors import error_response
from app.api.schemas.system import HealthResponse, ReadyResponse
from app.infrastructure.db.connection import probe_readiness


router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        500: error_response("Unexpected application failure."),
    },
)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: error_response("Service temporarily unavailable."),
        500: error_response("Unexpected application failure."),
    },
)
async def ready() -> ReadyResponse:
    await probe_readiness()
    return ReadyResponse(status="ready", database="ok")