from fastapi import APIRouter, HTTPException, status

from app.api.schemas.tasks import CreateTaskRequest, TaskResponse, TaskStartResponse
from app.domain.services.session_manager import SessionManager
from app.domain.services.task_service import OpenSessionExistsError, TaskNotFoundError, TaskService
from app.infrastructure.repositories.session_repository import SessionRepository
from app.infrastructure.repositories.task_repository import TaskRepository


router = APIRouter()

task_service = TaskService(
    task_repository=TaskRepository(),
    session_repository=SessionRepository(),
    session_manager=SessionManager(session_repository=SessionRepository()),
)


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def create_task(payload: CreateTaskRequest) -> TaskResponse:
    title = (payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title is required.")

    subject_id = str(payload.subject_id) if payload.subject_id else None
    try:
        return await task_service.create_task(title, subject_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create task.") from exc


@router.get("/tasks", response_model=list[TaskResponse], status_code=status.HTTP_200_OK)
async def list_tasks() -> list[TaskResponse]:
    try:
        return await task_service.list_tasks()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve tasks.") from exc


@router.post("/tasks/{task_id}/start", response_model=TaskStartResponse, status_code=status.HTTP_200_OK)
async def start_task(task_id: str) -> TaskStartResponse:
    try:
        return await task_service.start_task(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.") from exc
    except OpenSessionExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task already has an open session.") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start task.") from exc