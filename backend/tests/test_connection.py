from contextlib import asynccontextmanager

import pytest

from app.infrastructure.db import connection


class FakeAcquireContext:
    def __init__(self, *, value=None, exc: Exception | None = None):
        self._value = value
        self._exc = exc

    async def __aenter__(self):
        if self._exc is not None:
            raise self._exc
        return self._value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, *, connection_value=None, acquire_exc: Exception | None = None):
        self._connection_value = connection_value
        self._acquire_exc = acquire_exc
        self.closed = False

    def acquire(self):
        return FakeAcquireContext(value=self._connection_value, exc=self._acquire_exc)

    async def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def reset_pool() -> None:
    connection._pool = None
    yield
    connection._pool = None


def test_normalize_database_url_rewrites_postgres_scheme() -> None:
    assert connection._normalize_database_url("postgres://example.test/study-buddy") == "postgresql://example.test/study-buddy"
    assert connection._normalize_database_url("postgresql://example.test/study-buddy") == "postgresql://example.test/study-buddy"


@pytest.mark.asyncio
async def test_init_pool_raises_database_unavailable_when_pool_creation_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_create_pool(*args, **kwargs):
        raise RuntimeError("pool init failed")

    monkeypatch.setenv("DATABASE_URL", "postgres://example.test/study-buddy")
    monkeypatch.setattr(connection.asyncpg, "create_pool", fake_create_pool)

    with pytest.raises(connection.DatabaseUnavailableError):
        await connection.init_pool()


@pytest.mark.asyncio
async def test_get_connection_raises_database_unavailable_when_pool_acquire_fails() -> None:
    connection._pool = FakePool(acquire_exc=RuntimeError("acquire failed"))

    with pytest.raises(connection.DatabaseUnavailableError):
        async with connection.get_connection():
            pass


@pytest.mark.asyncio
async def test_close_pool_closes_and_clears_pool() -> None:
    fake_pool = FakePool(connection_value=object())
    connection._pool = fake_pool

    await connection.close_pool()

    assert fake_pool.closed is True
    assert connection._pool is None