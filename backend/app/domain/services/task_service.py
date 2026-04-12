from app.domain.engines.personalization_engine import calculate_planned_duration_minutes, select_next_task
from app.domain.engines.difficulty_reducer import reduce_instruction
from app.domain.engines.subtask_engine import generate_subtask
from app.infrastructure.db.connection import get_connection
from app.infrastructure.repositories.attempt_repository import AttemptRepository
from app.infrastructure.repositories.session_repository import SessionRepository
from app.infrastructure.repositories.subtask_repository import SubtaskRepository
from app.infrastructure.repositories.task_repository import TaskRepository


class TaskNotFoundError(Exception):
    pass


class TaskAlreadyCompletedError(Exception):
    pass


class OpenSessionExistsError(Exception):
    pass


class TaskService:
    def __init__(
        self,
        task_repository: TaskRepository,
        session_repository: SessionRepository,
        subtask_repository: SubtaskRepository,
        attempt_repository: AttemptRepository,
    ) -> None:
        self._task_repository = task_repository
        self._session_repository = session_repository
        self._subtask_repository = subtask_repository
        self._attempt_repository = attempt_repository

    async def create_task(self, title: str, subject_id: str | None = None) -> dict:
        return await self._task_repository.create_task(title, subject_id)

    async def list_tasks(self) -> list[dict]:
        return await self._task_repository.list_tasks()

    async def get_next_task(self) -> dict:
        task_candidates = await self._task_repository.get_next_task_candidates()
        task = select_next_task(task_candidates)
        if task is None:
            raise TaskNotFoundError()

        return {
            "id": task["id"],
            "title": task["title"],
            "subject_id": task["subject_id"],
            "created_at": task["created_at"],
            "is_completed": task["is_completed"],
        }

    async def start_task(self, task_id: str) -> dict:
        task = await self._task_repository.get_task(task_id)
        if task is None:
            raise TaskNotFoundError()

        if task["is_completed"]:
            raise TaskAlreadyCompletedError()

        open_session = await self._session_repository.get_open_session_for_task(task_id)
        if open_session is not None:
            raise OpenSessionExistsError()

        recent_attempts = await self._attempt_repository.get_recent_attempts(task_id)
        recent_completions = sum(1 for attempt in recent_attempts if attempt["outcome"] == "completed")
        recent_aborts = sum(1 for attempt in recent_attempts if attempt["outcome"] == "aborted")
        recent_session_durations = await self._session_repository.get_recent_task_duration_history(task_id)
        planned_duration_minutes = calculate_planned_duration_minutes(recent_session_durations)

        instruction = reduce_instruction(
            generate_subtask(task["title"]),
            {
                "recent_completions": recent_completions,
                "recent_aborts": recent_aborts,
            },
        )

        async with get_connection() as connection:
            async with connection.transaction():
                subtask = await self._subtask_repository.create_subtask(
                    task_id=task_id,
                    title=instruction["title"],
                    difficulty_level=instruction["difficulty_level"],
                    connection=connection,
                )
                session = await self._session_repository.create_session_in_connection(
                    connection=connection,
                    task_id=task_id,
                    subtask_id=subtask["id"],
                    planned_duration_minutes=planned_duration_minutes,
                )

        return {"session": session, "instruction": instruction}