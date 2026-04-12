from app.infrastructure.db.connection import get_connection
from app.infrastructure.repositories.attempt_repository import AttemptRepository
from app.infrastructure.repositories.session_repository import SessionRepository


class SessionNotFoundError(Exception):
    pass


class SessionAlreadyEndedError(Exception):
    pass


class SessionManager:
    def __init__(self, session_repository: SessionRepository, attempt_repository: AttemptRepository) -> None:
        self._session_repository = session_repository
        self._attempt_repository = attempt_repository

    async def complete_session(self, session_id: str) -> dict:
        session = await self._session_repository.get_session(session_id)
        if session is None:
            raise SessionNotFoundError()
        if session["ended_at"] is not None:
            raise SessionAlreadyEndedError()

        async with get_connection() as connection:
            async with connection.transaction():
                ended_session = await self._session_repository.end_session_tx(
                    connection=connection,
                    session_id=session_id,
                    was_completed=True,
                    was_aborted=False,
                )
                if ended_session is None:
                    raise SessionNotFoundError()
                await self._attempt_repository.create_attempt(connection, session_id, "completed")
                if ended_session["task_id"] is not None:
                    await self._session_repository.mark_task_completed_tx(connection, str(ended_session["task_id"]))

        return ended_session

    async def abort_session(self, session_id: str) -> dict:
        session = await self._session_repository.get_session(session_id)
        if session is None:
            raise SessionNotFoundError()
        if session["ended_at"] is not None:
            raise SessionAlreadyEndedError()

        async with get_connection() as connection:
            async with connection.transaction():
                ended_session = await self._session_repository.end_session_tx(
                    connection=connection,
                    session_id=session_id,
                    was_completed=False,
                    was_aborted=True,
                )
                if ended_session is None:
                    raise SessionNotFoundError()
                await self._attempt_repository.create_attempt(connection, session_id, "aborted")

        return ended_session