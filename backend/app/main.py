from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.sessions import router as sessions_router
from app.api.routes.subjects import router as subjects_router
from app.api.routes.tasks import router as tasks_router
from app.infrastructure.db.connection import DatabaseUnavailableError, close_pool, init_pool


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_pool()
    try:
        yield
    finally:
        await close_pool()


app = FastAPI(title="Study Buddy", lifespan=lifespan)


@app.exception_handler(DatabaseUnavailableError)
async def handle_database_unavailable(_: Request, __: DatabaseUnavailableError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "Service temporarily unavailable."},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)
app.include_router(subjects_router)
app.include_router(sessions_router)