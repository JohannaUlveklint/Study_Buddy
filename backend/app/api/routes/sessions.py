from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.errors import error_response
from app.api.schemas.sessions import SessionResponse
from app.domain.services.session_manager import (
    SessionAlreadyEndedError,
    SessionManager,
    SessionNotFoundError,
)
from app.infrastructure.db.connection import DatabaseUnavailableError
from app.infrastructure.repositories.attempt_repository import AttemptRepository
from app.infrastructure.repositories.session_repository import SessionRepository


router = APIRouter()

SESSION_ACTION_RESPONSES = {
    404: error_response("Session not found."),
    409: error_response("Session is already ended."),
    422: error_response("Request validation failed."),
    503: error_response("Service temporarily unavailable."),
    500: error_response("Contract violation or unexpected internal failure."),
}

session_manager = SessionManager(
    session_repository=SessionRepository(),
    attempt_repository=AttemptRepository(),
)


@router.post(
    "/sessions/{session_id}/complete",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    responses=SESSION_ACTION_RESPONSES,
)
async def complete_session(session_id: UUID) -> SessionResponse:
    try:
        return await session_manager.complete_session(str(session_id))
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.") from exc
    except SessionAlreadyEndedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is already ended.") from exc
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service temporarily unavailable.") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to complete session.") from exc


@router.post(
    "/sessions/{session_id}/abort",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    responses=SESSION_ACTION_RESPONSES,
)
async def abort_session(session_id: UUID) -> SessionResponse:
    try:
        return await session_manager.abort_session(str(session_id))
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.") from exc
    except SessionAlreadyEndedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is already ended.") from exc
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service temporarily unavailable.") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to abort session.") from exc