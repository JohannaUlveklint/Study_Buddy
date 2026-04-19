from uuid import UUID

from fastapi import APIRouter, HTTPException, status

import asyncpg

from app.api.schemas.errors import error_response
from app.api.schemas.tasks import CreateTaskRequest, TaskResponse, TaskStartResponse
from app.domain.services.task_service import OpenSessionExistsError, TaskAlreadyCompletedError, TaskNotFoundError, TaskService
from app.infrastructure.db.connection import DatabaseUnavailableError
from app.infrastructure.repositories.attempt_repository import AttemptRepository
from app.infrastructure.repositories.session_repository import SessionRepository
from app.infrastructure.repositories.subtask_repository import SubtaskRepository
from app.infrastructure.repositories.task_repository import TaskRepository


router = APIRouter()

TASK_CREATE_RESPONSES = {
    400: error_response("Subject not found."),
    422: error_response("Request validation failed."),
    503: error_response("Service temporarily unavailable."),
    500: error_response("Contract violation or unexpected internal failure."),
}

TASK_LIST_RESPONSES = {
    503: error_response("Service temporarily unavailable."),
    500: error_response("Contract violation or unexpected internal failure."),
}

TASK_START_RESPONSES = {
    404: error_response("Task not found."),
    409: error_response("Task state conflict."),
    422: error_response("Request validation failed."),
    503: error_response("Service temporarily unavailable."),
    500: error_response("Contract violation or unexpected internal failure."),
}

NEXT_TASK_RESPONSES = {
    404: error_response("No incomplete tasks."),
    503: error_response("Service temporarily unavailable."),
    500: error_response("Contract violation or unexpected internal failure."),
}

task_service = TaskService(
    task_repository=TaskRepository(),
    session_repository=SessionRepository(),
    subtask_repository=SubtaskRepository(),
    attempt_repository=AttemptRepository(),
)


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, responses=TASK_CREATE_RESPONSES)
async def create_task(payload: CreateTaskRequest) -> TaskResponse:
    subject_id = str(payload.subject_id) if payload.subject_id else None
    try:
        return await task_service.create_task(payload.title, subject_id)
    except asyncpg.ForeignKeyViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject not found.") from exc
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service temporarily unavailable.") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create task.") from exc


@router.get("/tasks", response_model=list[TaskResponse], status_code=status.HTTP_200_OK, responses=TASK_LIST_RESPONSES)
async def list_tasks() -> list[TaskResponse]:
    try:
        return await task_service.list_tasks()
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service temporarily unavailable.") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve tasks.") from exc


@router.post(
    "/tasks/{task_id}/start",
    response_model=TaskStartResponse,
    status_code=status.HTTP_200_OK,
    responses=TASK_START_RESPONSES,
)
async def start_task(task_id: UUID) -> TaskStartResponse:
    try:
        return await task_service.start_task(str(task_id))
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.") from exc
    except TaskAlreadyCompletedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task is already completed.") from exc
    except OpenSessionExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task already has an open session.") from exc
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service temporarily unavailable.") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start task.") from exc


@router.get("/next", response_model=TaskResponse, status_code=status.HTTP_200_OK, responses=NEXT_TASK_RESPONSES)
async def get_next_task() -> TaskResponse:
    try:
        task = await task_service.get_next_task()
        return task
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No incomplete tasks") from exc
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service temporarily unavailable.") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve next task.") from exc