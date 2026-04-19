from contextlib import asynccontextmanager
import json

import pytest

from app.api.routes import system as system_routes
from app.infrastructure.db.connection import DatabaseUnavailableError
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


async def _request(method: str, path: str) -> tuple[int, dict]:
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
        "headers": [(b"host", b"testserver")],
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
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    await app(scope, receive, send)

    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")

    return status, json.loads(response_body.decode("utf-8"))


@pytest.mark.asyncio
async def test_health_returns_liveness_without_touching_database(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called() -> None:
        raise AssertionError("readiness probe should not run for /health")

    monkeypatch.setattr(system_routes, "probe_readiness", fail_if_called)

    async with _lifespan(monkeypatch):
        status_code, response = await _request("GET", "/health")

    assert status_code == 200
    assert response == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_returns_readiness_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_probe() -> None:
        return None

    monkeypatch.setattr(system_routes, "probe_readiness", fake_probe)

    async with _lifespan(monkeypatch):
        status_code, response = await _request("GET", "/ready")

    assert status_code == 200
    assert response == {"status": "ready", "database": "ok"}


@pytest.mark.asyncio
async def test_ready_returns_shared_error_shape_when_database_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_probe() -> None:
        raise DatabaseUnavailableError("down")

    monkeypatch.setattr(system_routes, "probe_readiness", fake_probe)

    async with _lifespan(monkeypatch):
        status_code, response = await _request("GET", "/ready")

    assert status_code == 503
    assert response == {"detail": "Service temporarily unavailable."}