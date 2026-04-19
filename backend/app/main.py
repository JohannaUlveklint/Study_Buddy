from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.system import router as system_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.subjects import router as subjects_router
from app.api.routes.tasks import router as tasks_router
from app.api.schemas.errors import ErrorResponse
from app.infrastructure.db.connection import DatabaseUnavailableError, close_pool, init_pool


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_pool()
    try:
        yield
    finally:
        await close_pool()


app = FastAPI(title="Study Buddy", lifespan=lifespan)


def _error_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=ErrorResponse(detail=detail).model_dump())


@app.exception_handler(RequestValidationError)
async def handle_request_validation(_: Request, __: RequestValidationError) -> JSONResponse:
    return _error_response(422, "Request validation failed.")


@app.exception_handler(ResponseValidationError)
async def handle_response_validation(_: Request, __: ResponseValidationError) -> JSONResponse:
    return _error_response(500, "Response validation failed.")


@app.exception_handler(DatabaseUnavailableError)
async def handle_database_unavailable(_: Request, __: DatabaseUnavailableError) -> JSONResponse:
    return _error_response(503, "Service temporarily unavailable.")


@app.exception_handler(HTTPException)
async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _error_response(exc.status_code, detail)


@app.exception_handler(Exception)
async def handle_unexpected_exception(_: Request, __: Exception) -> JSONResponse:
    return _error_response(500, "Internal server error.")

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
app.include_router(system_router)