# backend/app/infrastructure/db/connection.py
from contextlib import asynccontextmanager
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[3] / ".env")

_pool: asyncpg.Pool | None = None


class DatabaseUnavailableError(Exception):
    pass


def _normalize_database_url(database_url: str | None) -> str:
    if not database_url:
        raise DatabaseUnavailableError("Database configuration is unavailable.")

    return database_url.replace("postgres://", "postgresql://", 1)


async def init_pool() -> None:
    global _pool

    if _pool is not None:
        return

    try:
        _pool = await asyncpg.create_pool(_normalize_database_url(os.getenv("DATABASE_URL")), ssl="require")
    except DatabaseUnavailableError:
        raise
    except Exception as exc:
        raise DatabaseUnavailableError("Database service is unavailable.") from exc


async def close_pool() -> None:
    global _pool

    if _pool is None:
        return

    pool = _pool
    _pool = None
    await pool.close()


@asynccontextmanager
async def get_connection():
    if _pool is None:
        raise DatabaseUnavailableError("Database service is unavailable.")

    try:
        async with _pool.acquire() as connection:
            yield connection
    except DatabaseUnavailableError:
        raise
    except Exception as exc:
        raise DatabaseUnavailableError("Database service is unavailable.") from exc
 