from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest

from app.domain.services import task_service as task_service_module
from app.domain.services.task_service import (
    OpenSessionExistsError,
    TaskAlreadyCompletedError,
    TaskNotFoundError,
    TaskService,
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


class RecordingTaskRepository:
    def __init__(self, *, task=None, candidates=None):
        self.task = task
        self.candidates = [] if candidates is None else candidates
        self.calls: list[tuple] = []

    async def create_task(self, title: str, subject_id: str | None = None) -> dict:
        raise AssertionError("Unexpected create_task call")

    async def list_tasks(self) -> list[dict]:
        raise AssertionError("Unexpected list_tasks call")

    async def get_next_task_candidates(self) -> list[dict]:
        self.calls.append(("get_next_task_candidates",))
        return self.candidates

    async def get_task_for_update(self, connection, task_id: str) -> dict | None:
        self.calls.append(("get_task_for_update", connection, task_id))
        return self.task


class RecordingSessionRepository:
    def __init__(self, *, open_session=None, duration_history=None, created_session=None):
        self.open_session = open_session
        self.duration_history = [] if duration_history is None else duration_history
        self.created_session = created_session
        self.calls: list[tuple] = []

    async def get_open_session_for_task_in_connection(self, connection, task_id: str) -> dict | None:
        self.calls.append(("get_open_session_for_task_in_connection", connection, task_id))
        return self.open_session

    async def get_recent_task_duration_history_in_connection(self, connection, task_id: str) -> list[dict]:
        self.calls.append(("get_recent_task_duration_history_in_connection", connection, task_id))
        return self.duration_history

    async def create_session_in_connection(
        self,
        connection,
        task_id: str,
        subtask_id: str | None,
        planned_duration_minutes: int,
    ) -> dict | None:
        self.calls.append(
            (
                "create_session_in_connection",
                connection,
                task_id,
                subtask_id,
                planned_duration_minutes,
            )
        )
        return self.created_session


class RecordingSubtaskRepository:
    def __init__(self, *, created_subtask=None):
        self.created_subtask = created_subtask
        self.calls: list[tuple] = []

    async def create_subtask(
        self,
        task_id: str,
        title: str,
        difficulty_level: int,
        connection=None,
    ) -> dict | None:
        self.calls.append(("create_subtask", connection, task_id, title, difficulty_level))
        return self.created_subtask


class RecordingAttemptRepository:
    def __init__(self, *, recent_attempts=None):
        self.recent_attempts = [] if recent_attempts is None else recent_attempts
        self.calls: list[tuple] = []

    async def get_recent_attempts_in_connection(self, connection, task_id: str, limit: int = 5) -> list[dict]:
        self.calls.append(("get_recent_attempts_in_connection", connection, task_id, limit))
        return self.recent_attempts


def _patch_connection(monkeypatch: pytest.MonkeyPatch, connection: FakeConnection) -> None:
    @asynccontextmanager
    async def fake_get_connection():
        yield connection

    monkeypatch.setattr(task_service_module, "get_connection", fake_get_connection)


def _build_service(*, task=None, open_session=None, recent_attempts=None, duration_history=None, created_subtask=None, created_session=None):
    return TaskService(
        task_repository=RecordingTaskRepository(task=task),
        session_repository=RecordingSessionRepository(
            open_session=open_session,
            duration_history=duration_history,
            created_session=created_session,
        ),
        subtask_repository=RecordingSubtaskRepository(created_subtask=created_subtask),
        attempt_repository=RecordingAttemptRepository(recent_attempts=recent_attempts),
    )


@pytest.mark.asyncio
async def test_get_next_task_raises_not_found_for_empty_candidates() -> None:
    service = TaskService(
        task_repository=RecordingTaskRepository(candidates=[]),
        session_repository=RecordingSessionRepository(),
        subtask_repository=RecordingSubtaskRepository(),
        attempt_repository=RecordingAttemptRepository(),
    )

    with pytest.raises(TaskNotFoundError):
        await service.get_next_task()


@pytest.mark.asyncio
async def test_get_next_task_returns_stripped_task_fields() -> None:
    candidate = {
        "id": "task-1",
        "title": "Read chapter",
        "subject_id": None,
        "created_at": datetime(2026, 4, 13, tzinfo=timezone.utc),
        "is_completed": False,
        "latest_ended_at": None,
        "latest_ended_was_aborted": None,
        "latest_started_at": None,
        "ended_abort_count": 0,
        "has_session_history": False,
    }
    service = TaskService(
        task_repository=RecordingTaskRepository(candidates=[candidate]),
        session_repository=RecordingSessionRepository(),
        subtask_repository=RecordingSubtaskRepository(),
        attempt_repository=RecordingAttemptRepository(),
    )

    result = await service.get_next_task()

    assert result == {
        "id": "task-1",
        "title": "Read chapter",
        "subject_id": None,
        "created_at": datetime(2026, 4, 13, tzinfo=timezone.utc),
        "is_completed": False,
    }


@pytest.mark.asyncio
async def test_start_task_raises_not_found_when_locked_task_lookup_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    service = _build_service(task=None)

    with pytest.raises(TaskNotFoundError):
        await service.start_task("task-123")

    assert connection.events == [("transaction_enter", None), ("transaction_exit", "TaskNotFoundError")]


@pytest.mark.asyncio
async def test_start_task_raises_conflict_when_task_is_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    service = _build_service(task={"id": "task-123", "title": "Write essay", "is_completed": True})

    with pytest.raises(TaskAlreadyCompletedError):
        await service.start_task("task-123")


@pytest.mark.asyncio
async def test_start_task_raises_conflict_when_open_session_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    service = _build_service(
        task={"id": "task-123", "title": "Write essay", "is_completed": False},
        open_session={"id": "session-1"},
    )

    with pytest.raises(OpenSessionExistsError):
        await service.start_task("task-123")


@pytest.mark.asyncio
async def test_start_task_rolls_back_when_subtask_write_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)
    service = _build_service(
        task={"id": "task-123", "title": "Write essay", "is_completed": False},
        recent_attempts=[],
        duration_history=[],
        created_subtask=None,
    )

    with pytest.raises(RuntimeError, match="Failed to create subtask"):
        await service.start_task("task-123")

    assert connection.events[-1] == ("transaction_exit", "RuntimeError")


@pytest.mark.asyncio
async def test_start_task_uses_one_connection_and_returns_existing_payload_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)

    task_repository = RecordingTaskRepository(
        task={
            "id": "task-123",
            "title": "Write essay",
            "subject_id": None,
            "created_at": datetime(2026, 4, 13, tzinfo=timezone.utc),
            "is_completed": False,
        }
    )
    session_repository = RecordingSessionRepository(
        open_session=None,
        duration_history=[
            {"actual_duration_minutes": 11},
            {"actual_duration_minutes": 12},
        ],
        created_session={
            "id": "session-1",
            "task_id": "task-123",
            "subtask_id": "subtask-1",
            "started_at": datetime(2026, 4, 13, 9, 0, tzinfo=timezone.utc),
            "ended_at": None,
            "planned_duration_minutes": 12,
            "actual_duration_minutes": None,
            "was_completed": False,
            "was_aborted": False,
        },
    )
    subtask_repository = RecordingSubtaskRepository(
        created_subtask={
            "id": "subtask-1",
            "task_id": "task-123",
            "title": "Write 3 sentences",
            "difficulty_level": 2,
            "is_completed": False,
        }
    )
    attempt_repository = RecordingAttemptRepository(
        recent_attempts=[
            {"outcome": "completed"},
            {"outcome": "completed"},
            {"outcome": "completed"},
            {"outcome": "completed"},
        ]
    )
    service = TaskService(
        task_repository=task_repository,
        session_repository=session_repository,
        subtask_repository=subtask_repository,
        attempt_repository=attempt_repository,
    )

    result = await service.start_task("task-123")

    assert result == {
        "session": session_repository.created_session,
        "instruction": {"title": "Write 3 sentences", "difficulty_level": 2},
    }
    assert task_repository.calls == [("get_task_for_update", connection, "task-123")]
    assert session_repository.calls == [
        ("get_open_session_for_task_in_connection", connection, "task-123"),
        ("get_recent_task_duration_history_in_connection", connection, "task-123"),
        ("create_session_in_connection", connection, "task-123", "subtask-1", 12),
    ]
    assert subtask_repository.calls == [
        ("create_subtask", connection, "task-123", "Write 3 sentences", 2)
    ]
    assert attempt_repository.calls == [
        ("get_recent_attempts_in_connection", connection, "task-123", 5)
    ]
    assert connection.events == [("transaction_enter", None), ("transaction_exit", None)]