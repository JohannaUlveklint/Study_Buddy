from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CreateTaskRequest(BaseModel):
    title: str | None = None
    subject_id: UUID | None = None


class TaskResponse(BaseModel):
    id: UUID
    title: str
    subject_id: UUID | None
    created_at: datetime
    is_completed: bool


class InstructionResponse(BaseModel):
    title: str
    difficulty_level: int


class TaskSessionResponse(BaseModel):
    id: UUID
    task_id: UUID | None
    subtask_id: UUID | None
    started_at: datetime
    ended_at: datetime | None
    planned_duration_minutes: int | None
    actual_duration_minutes: int | None
    was_completed: bool
    was_aborted: bool


class TaskStartResponse(BaseModel):
    session: TaskSessionResponse
    instruction: InstructionResponse