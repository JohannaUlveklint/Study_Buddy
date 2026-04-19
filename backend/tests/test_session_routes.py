import pytest
from fastapi import HTTPException
from uuid import uuid4

from app.api.routes import sessions as session_routes
from app.domain.services.session_manager import SessionAlreadyEndedError, SessionNotFoundError
from app.infrastructure.db.connection import DatabaseUnavailableError


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


def _async_raise(exc: Exception):
    async def _inner(*args, **kwargs):
        raise exc

    return _inner


@pytest.mark.asyncio
async def test_complete_session_returns_service_result(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = {"id": "session-1", "was_completed": True, "was_aborted": False}
    monkeypatch.setattr(session_routes.session_manager, "complete_session", _async_return(expected))

    assert await session_routes.complete_session(uuid4()) == expected


@pytest.mark.asyncio
async def test_complete_session_maps_not_found_to_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_routes.session_manager, "complete_session", _async_raise(SessionNotFoundError()))

    with pytest.raises(HTTPException) as exc_info:
        await session_routes.complete_session(uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Session not found."


@pytest.mark.asyncio
async def test_complete_session_maps_already_ended_to_409(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_routes.session_manager, "complete_session", _async_raise(SessionAlreadyEndedError()))

    with pytest.raises(HTTPException) as exc_info:
        await session_routes.complete_session(uuid4())

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Session is already ended."


@pytest.mark.asyncio
async def test_complete_session_maps_database_unavailable_to_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_routes.session_manager, "complete_session", _async_raise(DatabaseUnavailableError("down")))

    with pytest.raises(HTTPException) as exc_info:
        await session_routes.complete_session(uuid4())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Service temporarily unavailable."


@pytest.mark.asyncio
async def test_abort_session_maps_generic_failure_to_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_routes.session_manager, "abort_session", _async_raise(RuntimeError("boom")))

    with pytest.raises(HTTPException) as exc_info:
        await session_routes.abort_session(uuid4())

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to abort session."


@pytest.mark.asyncio
async def test_abort_session_returns_service_result(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = {"id": "session-1", "was_completed": False, "was_aborted": True}
    monkeypatch.setattr(session_routes.session_manager, "abort_session", _async_return(expected))

    assert await session_routes.abort_session(uuid4()) == expected


@pytest.mark.asyncio
async def test_abort_session_maps_not_found_to_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_routes.session_manager, "abort_session", _async_raise(SessionNotFoundError()))

    with pytest.raises(HTTPException) as exc_info:
        await session_routes.abort_session(uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Session not found."


@pytest.mark.asyncio
async def test_abort_session_maps_already_ended_to_409(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_routes.session_manager, "abort_session", _async_raise(SessionAlreadyEndedError()))

    with pytest.raises(HTTPException) as exc_info:
        await session_routes.abort_session(uuid4())

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Session is already ended."


@pytest.mark.asyncio
async def test_abort_session_maps_database_unavailable_to_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_routes.session_manager, "abort_session", _async_raise(DatabaseUnavailableError("down")))

    with pytest.raises(HTTPException) as exc_info:
        await session_routes.abort_session(uuid4())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Service temporarily unavailable."


@pytest.mark.asyncio
async def test_complete_session_maps_generic_failure_to_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_routes.session_manager, "complete_session", _async_raise(RuntimeError("boom")))

    with pytest.raises(HTTPException) as exc_info:
        await session_routes.complete_session(uuid4())

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to complete session."


def test_session_routes_document_shared_error_contract() -> None:
    complete_route = next(route for route in session_routes.router.routes if route.path == "/sessions/{session_id}/complete")
    abort_route = next(route for route in session_routes.router.routes if route.path == "/sessions/{session_id}/abort")

    assert 422 in complete_route.responses
    assert 500 in complete_route.responses
    assert 422 in abort_route.responses
    assert 503 in abort_route.responses