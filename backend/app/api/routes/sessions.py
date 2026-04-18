from fastapi import APIRouter, HTTPException, status

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

session_manager = SessionManager(
    session_repository=SessionRepository(),
    attempt_repository=AttemptRepository(),
)


@router.post("/sessions/{session_id}/complete", response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def complete_session(session_id: str) -> SessionResponse:
    try:
        return await session_manager.complete_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.") from exc
    except SessionAlreadyEndedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is already ended.") from exc
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service temporarily unavailable.") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to complete session.") from exc


@router.post("/sessions/{session_id}/abort", response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def abort_session(session_id: str) -> SessionResponse:
    try:
        return await session_manager.abort_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.") from exc
    except SessionAlreadyEndedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is already ended.") from exc
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service temporarily unavailable.") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to abort session.") from exc