from fastapi import HTTPException
import pytest

from app.api.routes import subjects as subject_routes
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
async def test_list_subjects_returns_service_result(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = [{"id": "subject-1", "name": "Math", "color": "#5865F2", "icon": "calculator"}]
    monkeypatch.setattr(subject_routes.subject_service, "list_subjects", _async_return(expected))

    assert await subject_routes.list_subjects() == expected


@pytest.mark.asyncio
async def test_list_subjects_maps_database_unavailable_to_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject_routes.subject_service, "list_subjects", _async_raise(DatabaseUnavailableError("down")))

    with pytest.raises(HTTPException) as exc_info:
        await subject_routes.list_subjects()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Service temporarily unavailable."


@pytest.mark.asyncio
async def test_list_subjects_maps_generic_failure_to_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject_routes.subject_service, "list_subjects", _async_raise(RuntimeError("boom")))

    with pytest.raises(HTTPException) as exc_info:
        await subject_routes.list_subjects()

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to retrieve subjects."