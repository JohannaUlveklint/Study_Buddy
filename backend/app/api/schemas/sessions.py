from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: UUID
    task_id: UUID | None
    subtask_id: UUID | None
    started_at: datetime
    ended_at: datetime | None
    planned_duration_minutes: int | None
    actual_duration_minutes: int | None
    was_completed: bool
    was_aborted: bool