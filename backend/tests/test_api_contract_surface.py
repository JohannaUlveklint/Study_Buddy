from contextlib import asynccontextmanager
import json
from uuid import uuid4

import pytest

from app.api.routes import sessions as session_routes
from app.api.routes import subjects as subject_routes
from app.api.routes import tasks as task_routes
from app.main import app
import app.main as app_main


@asynccontextmanager
async def _lifespan(monkeypatch: pytest.MonkeyPatch):
    async def fake_init_pool() -> None:
        return None

    async def fake_close_pool() -> None:
        return None

    monkeypatch.setattr(app_main, "init_pool", fake_init_pool)
    monkeypatch.setattr(app_main, "close_pool", fake_close_pool)

    async with app.router.lifespan_context(app):
        yield


async def _request(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    messages: list[dict] = []
    request_sent = False

    headers = [(b"host", b"testserver")]
    if payload is not None:
        headers.extend(
            [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("utf-8")),
            ]
        )

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": headers,
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
async def test_openapi_documents_phase_seven_contract_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    async with _lifespan(monkeypatch):
        status_code, document = await _request("GET", "/openapi.json")

    assert status_code == 200
    paths = document["paths"]
    assert "/tasks" in paths
    assert "/tasks/{task_id}/start" in paths
    assert "/sessions/{session_id}/complete" in paths
    assert "/sessions/{session_id}/abort" in paths
    assert "/subjects" in paths
    assert "/next" in paths
    assert "/health" in paths
    assert "/ready" in paths
    assert "ErrorResponse" in document["components"]["schemas"]

    error_ref = "#/components/schemas/ErrorResponse"
    documented_error_responses = [
        ("/tasks", "post", ["400", "422", "503", "500"]),
        ("/tasks", "get", ["503", "500"]),
        ("/tasks/{task_id}/start", "post", ["404", "409", "422", "503", "500"]),
        ("/sessions/{session_id}/complete", "post", ["404", "409", "422", "503", "500"]),
        ("/sessions/{session_id}/abort", "post", ["404", "409", "422", "503", "500"]),
        ("/subjects", "get", ["503", "500"]),
        ("/next", "get", ["404", "503", "500"]),
        ("/health", "get", ["500"]),
        ("/ready", "get", ["503", "500"]),
    ]

    for path, method, status_codes in documented_error_responses:
        responses = paths[path][method]["responses"]
        for status_code in status_codes:
            assert responses[status_code]["content"]["application/json"]["schema"]["$ref"] == error_ref


@pytest.mark.asyncio
async def test_invalid_task_payload_fails_at_boundary_before_service_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("task service should not run for invalid payload")

    monkeypatch.setattr(task_routes.task_service, "create_task", fail_if_called)

    async with _lifespan(monkeypatch):
        status_code, response = await _request("POST", "/tasks", {"title": "   "})

    assert status_code == 422
    assert response == {"detail": "Request validation failed."}


@pytest.mark.asyncio
async def test_invalid_uuid_path_fails_at_boundary_before_service_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("task service should not run for invalid path parameter")

    monkeypatch.setattr(task_routes.task_service, "start_task", fail_if_called)

    async with _lifespan(monkeypatch):
        status_code, response = await _request("POST", "/tasks/not-a-uuid/start")

    assert status_code == 422
    assert response == {"detail": "Request validation failed."}


@pytest.mark.asyncio
async def test_invalid_response_payload_becomes_contract_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_list_subjects() -> list[dict]:
        return [{"id": "not-a-uuid", "name": "Math", "color": "#5865F2", "icon": "calculator"}]

    monkeypatch.setattr(subject_routes.subject_service, "list_subjects", fake_list_subjects)

    async with _lifespan(monkeypatch):
        status_code, response = await _request("GET", "/subjects")

    assert status_code == 500
    assert response == {"detail": "Response validation failed."}


@pytest.mark.asyncio
async def test_existing_user_flow_contract_remains_runnable(monkeypatch: pytest.MonkeyPatch) -> None:
    task_id = uuid4()
    session_id = uuid4()
    subject_id = uuid4()

    async def fake_list_subjects() -> list[dict]:
        return [{"id": str(subject_id), "name": "Math", "color": "#5865F2", "icon": "calculator"}]

    async def fake_create_task(title: str, provided_subject_id: str | None) -> dict:
        assert title == "Read chapter"
        assert provided_subject_id == str(subject_id)
        return {
            "id": str(task_id),
            "title": title,
            "subject_id": str(subject_id),
            "created_at": "2026-04-18T12:00:00Z",
            "is_completed": False,
        }

    async def fake_start_task(provided_task_id: str) -> dict:
        assert provided_task_id == str(task_id)
        return {
            "session": {
                "id": str(session_id),
                "task_id": str(task_id),
                "subtask_id": str(uuid4()),
                "started_at": "2026-04-18T12:00:00Z",
                "ended_at": None,
                "planned_duration_minutes": 10,
                "actual_duration_minutes": None,
                "was_completed": False,
                "was_aborted": False,
            },
            "instruction": {"title": "Read 1 page", "difficulty_level": 1},
        }

    async def fake_complete_session(provided_session_id: str) -> dict:
        assert provided_session_id == str(session_id)
        return {
            "id": str(session_id),
            "task_id": str(task_id),
            "subtask_id": str(uuid4()),
            "started_at": "2026-04-18T12:00:00Z",
            "ended_at": "2026-04-18T12:10:00Z",
            "planned_duration_minutes": 10,
            "actual_duration_minutes": 10,
            "was_completed": True,
            "was_aborted": False,
        }

    async def fake_get_next_task() -> dict:
        return {
            "id": str(uuid4()),
            "title": "Write summary",
            "subject_id": str(subject_id),
            "created_at": "2026-04-18T12:15:00Z",
            "is_completed": False,
        }

    monkeypatch.setattr(subject_routes.subject_service, "list_subjects", fake_list_subjects)
    monkeypatch.setattr(task_routes.task_service, "create_task", fake_create_task)
    monkeypatch.setattr(task_routes.task_service, "start_task", fake_start_task)
    monkeypatch.setattr(session_routes.session_manager, "complete_session", fake_complete_session)
    monkeypatch.setattr(task_routes.task_service, "get_next_task", fake_get_next_task)

    async with _lifespan(monkeypatch):
        subjects_status, subjects_response = await _request("GET", "/subjects")
        create_status, create_response = await _request("POST", "/tasks", {"title": "  Read chapter  ", "subject_id": str(subject_id)})
        start_status, start_response = await _request("POST", f"/tasks/{task_id}/start")
        complete_status, complete_response = await _request("POST", f"/sessions/{session_id}/complete")
        next_status, next_response = await _request("GET", "/next")

    assert subjects_status == 200
    assert subjects_response == [{"id": str(subject_id), "name": "Math", "color": "#5865F2", "icon": "calculator"}]
    assert create_status == 201
    assert create_response["title"] == "Read chapter"
    assert start_status == 200
    assert start_response["session"]["id"] == str(session_id)
    assert complete_status == 200
    assert complete_response["was_completed"] is True
    assert next_status == 200
    assert next_response["title"] == "Write summary"