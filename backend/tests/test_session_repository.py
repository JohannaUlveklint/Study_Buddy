from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest

from app.infrastructure.repositories import session_repository
from app.infrastructure.repositories.session_repository import SessionRepository


class FakeConnection:
    def __init__(self, *, fetch_result=None, fetchrow_result=None):
        self.fetch_result = fetch_result if fetch_result is not None else []
        self.fetchrow_result = fetchrow_result
        self.fetch_calls = []
        self.fetchrow_calls = []

    async def fetch(self, query, *args):
        self.fetch_calls.append((query, args))
        return self.fetch_result

    async def fetchrow(self, query, *args):
        self.fetchrow_calls.append((query, args))
        return self.fetchrow_result


def _patch_connection(monkeypatch: pytest.MonkeyPatch, connection: FakeConnection) -> None:
    @asynccontextmanager
    async def fake_get_connection():
        yield connection

    monkeypatch.setattr(session_repository, "get_connection", fake_get_connection)


@pytest.mark.asyncio
async def test_get_recent_task_duration_history_filters_orders_and_limits_results(monkeypatch: pytest.MonkeyPatch) -> None:
    ended_at = datetime(2026, 4, 12, 10, 0, tzinfo=timezone.utc)
    connection = FakeConnection(
        fetch_result=[
            {"actual_duration_minutes": 14, "ended_at": ended_at},
            {"actual_duration_minutes": 9, "ended_at": ended_at.replace(hour=9)},
        ]
    )
    _patch_connection(monkeypatch, connection)

    repository = SessionRepository()
    history = await repository.get_recent_task_duration_history("task-123")

    assert history == [
        {"actual_duration_minutes": 14},
        {"actual_duration_minutes": 9},
    ]
    assert len(connection.fetch_calls) == 1
    query, args = connection.fetch_calls[0]
    assert args == ("task-123",)
    assert "ended_at IS NOT NULL" in query
    assert "actual_duration_minutes IS NOT NULL" in query
    assert "ORDER BY ended_at DESC" in query
    assert "LIMIT 5" in query


@pytest.mark.asyncio
async def test_end_session_tx_persists_actual_duration_minutes_and_serializes_response() -> None:
    record = {
        "id": "session-1",
        "task_id": "task-1",
        "subtask_id": "subtask-1",
        "started_at": datetime(2026, 4, 12, 9, 0, tzinfo=timezone.utc),
        "ended_at": datetime(2026, 4, 12, 9, 17, tzinfo=timezone.utc),
        "planned_duration_minutes": 15,
        "actual_duration_minutes": 17,
        "was_completed": True,
        "was_aborted": False,
    }
    connection = FakeConnection(fetchrow_result=record)

    repository = SessionRepository()
    ended_session = await repository.end_session_tx(
        connection,
        "session-1",
        was_completed=True,
        was_aborted=False,
    )

    assert ended_session == record
    assert len(connection.fetchrow_calls) == 1
    query, args = connection.fetchrow_calls[0]
    assert args == ("session-1", True, False)
    assert "SET ended_at = NOW()" in query
    assert "actual_duration_minutes = GREATEST(1, CEILING(EXTRACT(EPOCH FROM (NOW() - started_at)) / 60.0))::int" in query
    assert "was_completed = $2" in query
    assert "was_aborted = $3" in query
    assert "WHERE id = $1 AND ended_at IS NULL" in query