from app.domain.engines.difficulty_reducer import reduce_instruction
from app.domain.engines.subtask_engine import generate_subtask
from app.domain.services.session_manager import SessionManager
from app.infrastructure.repositories.session_repository import SessionRepository
from app.infrastructure.repositories.task_repository import TaskRepository


class TaskNotFoundError(Exception):
    pass


class OpenSessionExistsError(Exception):
    pass


class TaskService:
    def __init__(
        self,
        task_repository: TaskRepository,
        session_repository: SessionRepository,
        session_manager: SessionManager,
    ) -> None:
        self._task_repository = task_repository
        self._session_repository = session_repository
        self._session_manager = session_manager

    async def create_task(self, title: str, subject_id: str | None = None) -> dict:
        return await self._task_repository.create_task(title, subject_id)

    async def list_tasks(self) -> list[dict]:
        return await self._task_repository.list_tasks()

    async def start_task(self, task_id: str) -> dict:
        task = await self._task_repository.get_task(task_id)
        if task is None:
            raise TaskNotFoundError()

        open_session = await self._session_repository.get_open_session_for_task(task_id)
        if open_session is not None:
            raise OpenSessionExistsError()

        instruction = reduce_instruction(generate_subtask(task["title"]))
        session = await self._session_manager.create_session(task_id=task_id, subtask_id=None)

        return {"session": session, "instruction": instruction}