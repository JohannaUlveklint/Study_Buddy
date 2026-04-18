from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest

from app.domain.services import session_manager as session_manager_module
from app.domain.services.session_manager import (
    SessionAlreadyEndedError,
    SessionManager,
    SessionNotFoundError,
)


class FakeTransaction:
    def __init__(self, events: list[tuple[str, str | None]]):
        self._events = events

    async def __aenter__(self):
        self._events.append(("transaction_enter", None))
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._events.append(("transaction_exit", None if exc_type is None else exc_type.__name__))
        return False


class FakeConnection:
    def __init__(self):
        self.events: list[tuple[str, str | None]] = []

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self.events)


class RecordingSessionRepository:
    def __init__(self, *, session=None, ended_session=None):
        self.session = session
        self.ended_session = ended_session
        self.calls: list[tuple] = []

    async def get_session_in_connection(self, connection, session_id: str) -> dict | None:
        self.calls.append(("get_session_in_connection", connection, session_id))
        return self.session

    async def end_session_tx(self, connection, session_id: str, *, was_completed: bool = False, was_aborted: bool = False) -> dict | None:
        self.calls.append(("end_session_tx", connection, session_id, was_completed, was_aborted))
        return self.ended_session

    async def mark_task_completed_tx(self, connection, task_id: str) -> None:
        self.calls.append(("mark_task_completed_tx", connection, task_id))


class RecordingAttemptRepository:
    def __init__(self, *, exc: Exception | None = None):
        self.exc = exc
        self.calls: list[tuple] = []

    async def create_attempt(self, connection, session_id: str, outcome: str) -> int:
        self.calls.append(("create_attempt", connection, session_id, outcome))
        if self.exc is not None:
            raise self.exc
        return 1


def _patch_connection(monkeypatch: pytest.MonkeyPatch, connection: FakeConnection) -> None:
    @asynccontextmanager
    async def fake_get_connection():
        yield connection

    monkeypatch.setattr(session_manager_module, "get_connection", fake_get_connection)


@pytest.mark.asyncio
async def test_complete_session_raises_not_found_when_session_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    manager = SessionManager(
        session_repository=RecordingSessionRepository(session=None),
        attempt_repository=RecordingAttemptRepository(),
    )

    with pytest.raises(SessionNotFoundError):
        await manager.complete_session("session-1")

    assert connection.events == [("transaction_enter", None), ("transaction_exit", "SessionNotFoundError")]


@pytest.mark.asyncio
async def test_complete_session_raises_conflict_when_session_is_already_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    manager = SessionManager(
        session_repository=RecordingSessionRepository(
            session={"id": "session-1", "ended_at": datetime(2026, 4, 13, tzinfo=timezone.utc)}
        ),
        attempt_repository=RecordingAttemptRepository(),
    )

    with pytest.raises(SessionAlreadyEndedError):
        await manager.complete_session("session-1")


@pytest.mark.asyncio
async def test_complete_session_treats_missing_end_row_as_already_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    manager = SessionManager(
        session_repository=RecordingSessionRepository(
            session={"id": "session-1", "task_id": "task-1", "ended_at": None},
            ended_session=None,
        ),
        attempt_repository=RecordingAttemptRepository(),
    )

    with pytest.raises(SessionAlreadyEndedError):
        await manager.complete_session("session-1")


@pytest.mark.asyncio
async def test_complete_session_requires_attempt_write_before_marking_task_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    session_repository = RecordingSessionRepository(
        session={"id": "session-1", "task_id": "task-1", "ended_at": None},
        ended_session={
            "id": "session-1",
            "task_id": "task-1",
            "subtask_id": "subtask-1",
            "started_at": datetime(2026, 4, 13, 9, 0, tzinfo=timezone.utc),
            "ended_at": datetime(2026, 4, 13, 9, 12, tzinfo=timezone.utc),
            "planned_duration_minutes": 10,
            "actual_duration_minutes": 12,
            "was_completed": True,
            "was_aborted": False,
        },
    )
    manager = SessionManager(
        session_repository=session_repository,
        attempt_repository=RecordingAttemptRepository(exc=RuntimeError("Failed to create attempt.")),
    )

    with pytest.raises(RuntimeError, match="Failed to create attempt"):
        await manager.complete_session("session-1")

    assert ("mark_task_completed_tx", connection, "task-1") not in session_repository.calls
    assert connection.events[-1] == ("transaction_exit", "RuntimeError")


@pytest.mark.asyncio
async def test_complete_session_marks_task_completed_after_attempt_and_returns_session(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    ended_session = {
        "id": "session-1",
        "task_id": "task-1",
        "subtask_id": "subtask-1",
        "started_at": datetime(2026, 4, 13, 9, 0, tzinfo=timezone.utc),
        "ended_at": datetime(2026, 4, 13, 9, 15, tzinfo=timezone.utc),
        "planned_duration_minutes": 10,
        "actual_duration_minutes": 15,
        "was_completed": True,
        "was_aborted": False,
    }
    session_repository = RecordingSessionRepository(
        session={"id": "session-1", "task_id": "task-1", "ended_at": None},
        ended_session=ended_session,
    )
    attempt_repository = RecordingAttemptRepository()
    manager = SessionManager(
        session_repository=session_repository,
        attempt_repository=attempt_repository,
    )

    result = await manager.complete_session("session-1")

    assert result == ended_session
    assert session_repository.calls == [
        ("get_session_in_connection", connection, "session-1"),
        ("end_session_tx", connection, "session-1", True, False),
        ("mark_task_completed_tx", connection, "task-1"),
    ]
    assert attempt_repository.calls == [("create_attempt", connection, "session-1", "completed")]
    assert connection.events == [("transaction_enter", None), ("transaction_exit", None)]


@pytest.mark.asyncio
async def test_abort_session_keeps_task_uncompleted_and_returns_session(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    ended_session = {
        "id": "session-1",
        "task_id": "task-1",
        "subtask_id": "subtask-1",
        "started_at": datetime(2026, 4, 13, 9, 0, tzinfo=timezone.utc),
        "ended_at": datetime(2026, 4, 13, 9, 3, tzinfo=timezone.utc),
        "planned_duration_minutes": 10,
        "actual_duration_minutes": 3,
        "was_completed": False,
        "was_aborted": True,
    }
    session_repository = RecordingSessionRepository(
        session={"id": "session-1", "task_id": "task-1", "ended_at": None},
        ended_session=ended_session,
    )
    attempt_repository = RecordingAttemptRepository()
    manager = SessionManager(
        session_repository=session_repository,
        attempt_repository=attempt_repository,
    )

    result = await manager.abort_session("session-1")

    assert result == ended_session
    assert session_repository.calls == [
        ("get_session_in_connection", connection, "session-1"),
        ("end_session_tx", connection, "session-1", False, True),
    ]
    assert attempt_repository.calls == [("create_attempt", connection, "session-1", "aborted")]


@pytest.mark.asyncio
async def test_abort_session_raises_not_found_when_session_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    manager = SessionManager(
        session_repository=RecordingSessionRepository(session=None),
        attempt_repository=RecordingAttemptRepository(),
    )

    with pytest.raises(SessionNotFoundError):
        await manager.abort_session("session-1")

    assert connection.events == [("transaction_enter", None), ("transaction_exit", "SessionNotFoundError")]


@pytest.mark.asyncio
async def test_abort_session_raises_conflict_when_session_is_already_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    manager = SessionManager(
        session_repository=RecordingSessionRepository(
            session={"id": "session-1", "ended_at": datetime(2026, 4, 13, tzinfo=timezone.utc)}
        ),
        attempt_repository=RecordingAttemptRepository(),
    )

    with pytest.raises(SessionAlreadyEndedError):
        await manager.abort_session("session-1")


@pytest.mark.asyncio
async def test_abort_session_treats_missing_end_row_as_already_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    manager = SessionManager(
        session_repository=RecordingSessionRepository(
            session={"id": "session-1", "task_id": "task-1", "ended_at": None},
            ended_session=None,
        ),
        attempt_repository=RecordingAttemptRepository(),
    )

    with pytest.raises(SessionAlreadyEndedError):
        await manager.abort_session("session-1")


@pytest.mark.asyncio
async def test_abort_session_rolls_back_when_attempt_write_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    manager = SessionManager(
        session_repository=RecordingSessionRepository(
            session={"id": "session-1", "task_id": "task-1", "ended_at": None},
            ended_session={
                "id": "session-1",
                "task_id": "task-1",
                "subtask_id": None,
                "started_at": datetime(2026, 4, 13, 9, 0, tzinfo=timezone.utc),
                "ended_at": datetime(2026, 4, 13, 9, 3, tzinfo=timezone.utc),
                "planned_duration_minutes": 10,
                "actual_duration_minutes": 3,
                "was_completed": False,
                "was_aborted": True,
            },
        ),
        attempt_repository=RecordingAttemptRepository(exc=RuntimeError("Failed to create attempt.")),
    )

    with pytest.raises(RuntimeError, match="Failed to create attempt"):
        await manager.abort_session("session-1")

    assert connection.events[-1] == ("transaction_exit", "RuntimeError")