import json

from fastapi import FastAPI, HTTPException
import pytest

from app.api.routes import tasks as task_routes
from app.api.schemas.tasks import CreateTaskRequest
from app.domain.services.task_service import OpenSessionExistsError, TaskAlreadyCompletedError, TaskNotFoundError
from app.infrastructure.db.connection import DatabaseUnavailableError


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


def _async_raise(exc: Exception):
    async def _inner(*args, **kwargs):
        raise exc

    return _inner


async def _request_json(app: FastAPI, method: str, path: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    messages: list[dict] = []
    request_sent = False

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("utf-8")),
        ],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
        "app": app,
    }

    async def receive() -> dict:
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}

        request_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    await app(scope, receive, send)

    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")

    return status, json.loads(response_body.decode("utf-8"))


@pytest.mark.asyncio
async def test_create_task_returns_service_result_and_trims_title(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str | None] = {}

    async def fake_create_task(title: str, subject_id: str | None) -> dict:
        captured["title"] = title
        captured["subject_id"] = subject_id
        return {"id": "task-1", "title": title, "subject_id": subject_id, "created_at": "now", "is_completed": False}

    monkeypatch.setattr(task_routes.task_service, "create_task", fake_create_task)

    result = await task_routes.create_task(CreateTaskRequest(title="  Read chapter  "))

    assert result["title"] == "Read chapter"
    assert captured == {"title": "Read chapter", "subject_id": None}


@pytest.mark.asyncio
async def test_create_task_rejects_blank_title() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await task_routes.create_task(CreateTaskRequest(title="   "))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Title is required."


@pytest.mark.asyncio
async def test_create_task_maps_foreign_key_error_to_400(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeForeignKeyViolationError(Exception):
        pass

    monkeypatch.setattr(task_routes.asyncpg, "ForeignKeyViolationError", FakeForeignKeyViolationError)
    monkeypatch.setattr(task_routes.task_service, "create_task", _async_raise(FakeForeignKeyViolationError()))

    with pytest.raises(HTTPException) as exc_info:
        await task_routes.create_task(CreateTaskRequest(title="Read chapter"))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Subject not found."


@pytest.mark.asyncio
async def test_create_task_maps_database_unavailable_to_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_routes.task_service, "create_task", _async_raise(DatabaseUnavailableError("down")))

    with pytest.raises(HTTPException) as exc_info:
        await task_routes.create_task(CreateTaskRequest(title="Read chapter"))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Service temporarily unavailable."


@pytest.mark.asyncio
async def test_create_task_returns_422_for_invalid_payload() -> None:
    app = FastAPI()
    app.include_router(task_routes.router)

    status_code, response = await _request_json(
        app,
        "POST",
        "/tasks",
        {"title": "Read chapter", "subject_id": "not-a-uuid"},
    )

    assert status_code == 422
    assert response["detail"]


@pytest.mark.asyncio
async def test_list_tasks_maps_generic_failure_to_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_routes.task_service, "list_tasks", _async_raise(RuntimeError("boom")))

    with pytest.raises(HTTPException) as exc_info:
        await task_routes.list_tasks()

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to retrieve tasks."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "detail"),
    [
        (TaskAlreadyCompletedError(), "Task is already completed."),
        (OpenSessionExistsError(), "Task already has an open session."),
    ],
)
async def test_start_task_maps_conflicts_to_409(monkeypatch: pytest.MonkeyPatch, error: Exception, detail: str) -> None:
    monkeypatch.setattr(task_routes.task_service, "start_task", _async_raise(error))

    with pytest.raises(HTTPException) as exc_info:
        await task_routes.start_task("task-1")

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == detail


@pytest.mark.asyncio
async def test_start_task_maps_not_found_to_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_routes.task_service, "start_task", _async_raise(TaskNotFoundError()))

    with pytest.raises(HTTPException) as exc_info:
        await task_routes.start_task("task-1")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Task not found."


@pytest.mark.asyncio
async def test_get_next_task_maps_not_found_to_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_routes.task_service, "get_next_task", _async_raise(TaskNotFoundError()))

    with pytest.raises(HTTPException) as exc_info:
        await task_routes.get_next_task()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "No incomplete tasks"


@pytest.mark.asyncio
async def test_get_next_task_maps_database_unavailable_to_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_routes.task_service, "get_next_task", _async_raise(DatabaseUnavailableError("down")))

    with pytest.raises(HTTPException) as exc_info:
        await task_routes.get_next_task()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Service temporarily unavailable."


@pytest.mark.asyncio
async def test_get_next_task_maps_generic_failure_to_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_routes.task_service, "get_next_task", _async_raise(RuntimeError("boom")))

    with pytest.raises(HTTPException) as exc_info:
        await task_routes.get_next_task()

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to retrieve next task."


@pytest.mark.asyncio
async def test_list_tasks_returns_service_result(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = [{"id": "task-1", "title": "Read", "subject_id": None, "created_at": "now", "is_completed": False}]
    monkeypatch.setattr(task_routes.task_service, "list_tasks", _async_return(expected))

    assert await task_routes.list_tasks() == expected


@pytest.mark.asyncio
async def test_list_tasks_maps_database_unavailable_to_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_routes.task_service, "list_tasks", _async_raise(DatabaseUnavailableError("down")))

    with pytest.raises(HTTPException) as exc_info:
        await task_routes.list_tasks()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Service temporarily unavailable."


@pytest.mark.asyncio
async def test_create_task_maps_generic_failure_to_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_routes.task_service, "create_task", _async_raise(RuntimeError("boom")))

    with pytest.raises(HTTPException) as exc_info:
        await task_routes.create_task(CreateTaskRequest(title="Read chapter"))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to create task."


@pytest.mark.asyncio
async def test_start_task_returns_service_result(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = {"session": {"id": "s-1"}, "instruction": {"title": "Read 2 pages", "difficulty_level": 1}}
    monkeypatch.setattr(task_routes.task_service, "start_task", _async_return(expected))

    assert await task_routes.start_task("task-1") == expected


@pytest.mark.asyncio
async def test_start_task_maps_database_unavailable_to_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_routes.task_service, "start_task", _async_raise(DatabaseUnavailableError("down")))

    with pytest.raises(HTTPException) as exc_info:
        await task_routes.start_task("task-1")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Service temporarily unavailable."


@pytest.mark.asyncio
async def test_start_task_maps_generic_failure_to_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_routes.task_service, "start_task", _async_raise(RuntimeError("boom")))

    with pytest.raises(HTTPException) as exc_info:
        await task_routes.start_task("task-1")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to start task."