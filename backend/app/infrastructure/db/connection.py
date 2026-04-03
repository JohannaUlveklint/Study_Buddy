# backend/app/infrastructure/db/connection.py
from contextlib import asynccontextmanager
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[3] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set.")

# asyncpg requires postgresql:// scheme; Supabase sometimes provides postgres://
_asyncpg_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)


@asynccontextmanager
async def get_connection():
    connection = await asyncpg.connect(_asyncpg_url, ssl="require")
    try:
        yield connection
    finally:
        await connection.close()
 