from app.infrastructure.db.connection import get_connection


def _serialize_session(record) -> dict | None:
    if record is None:
        return None

    return {
        "id": record["id"],
        "task_id": record["task_id"],
        "subtask_id": record["subtask_id"],
        "started_at": record["started_at"],
        "ended_at": record["ended_at"],
        "planned_duration_minutes": record["planned_duration_minutes"],
        "actual_duration_minutes": record["actual_duration_minutes"],
        "was_completed": record["was_completed"],
        "was_aborted": record["was_aborted"],
    }


async def _insert_session_record(connection, task_id: str, subtask_id: str | None, planned_duration_minutes: int):
    query = """
        INSERT INTO sessions (task_id, subtask_id, planned_duration_minutes)
        VALUES ($1, $2, $3)
        RETURNING id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes,
                  actual_duration_minutes, was_completed, was_aborted
    """

    return await connection.fetchrow(query, task_id, subtask_id, planned_duration_minutes)


class SessionRepository:
    async def get_recent_task_duration_history(self, task_id: str) -> list[dict]:
        async with get_connection() as connection:
            return await self.get_recent_task_duration_history_in_connection(connection, task_id)

    async def get_recent_task_duration_history_in_connection(self, connection, task_id: str) -> list[dict]:
        query = """
            SELECT actual_duration_minutes
            FROM sessions
            WHERE task_id = $1
              AND ended_at IS NOT NULL
              AND actual_duration_minutes IS NOT NULL
            ORDER BY ended_at DESC
            LIMIT 5
        """

        records = await connection.fetch(query, task_id)

        return [{"actual_duration_minutes": record["actual_duration_minutes"]} for record in records]

    async def get_open_session_for_task(self, task_id: str) -> dict | None:
        async with get_connection() as connection:
            return await self.get_open_session_for_task_in_connection(connection, task_id)

    async def get_open_session_for_task_in_connection(self, connection, task_id: str) -> dict | None:
        query = """
            SELECT id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes,
                   actual_duration_minutes, was_completed, was_aborted
            FROM sessions
            WHERE task_id = $1 AND ended_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
        """

        record = await connection.fetchrow(query, task_id)

        return _serialize_session(record)

    async def create_session(self, task_id: str, subtask_id: str | None, planned_duration_minutes: int) -> dict:
        async with get_connection() as connection:
            record = await _insert_session_record(connection, task_id, subtask_id, planned_duration_minutes)

        return _serialize_session(record)

    async def create_session_in_connection(
        self,
        connection,
        task_id: str,
        subtask_id: str | None,
        planned_duration_minutes: int,
    ) -> dict:
        record = await _insert_session_record(connection, task_id, subtask_id, planned_duration_minutes)

        return _serialize_session(record)

    async def get_session(self, session_id: str) -> dict | None:
        async with get_connection() as connection:
            return await self.get_session_in_connection(connection, session_id)

    async def get_session_in_connection(self, connection, session_id: str) -> dict | None:
        query = """
            SELECT id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes,
                   actual_duration_minutes, was_completed, was_aborted
            FROM sessions
            WHERE id = $1
        """

        record = await connection.fetchrow(query, session_id)

        return _serialize_session(record)

    async def end_session_tx(
        self,
        connection,
        session_id: str,
        *,
        was_completed: bool = False,
        was_aborted: bool = False,
    ) -> dict:
        query = """
            UPDATE sessions
            SET ended_at = NOW(),
                actual_duration_minutes = GREATEST(1, CEILING(EXTRACT(EPOCH FROM (NOW() - started_at)) / 60.0))::int,
                was_completed = $2,
                was_aborted = $3
            WHERE id = $1 AND ended_at IS NULL
            RETURNING id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes,
                      actual_duration_minutes, was_completed, was_aborted
        """

        record = await connection.fetchrow(query, session_id, was_completed, was_aborted)

        return _serialize_session(record)

    async def mark_task_completed_tx(self, connection, task_id: str) -> None:
        await connection.execute(
            "UPDATE tasks SET is_completed = TRUE WHERE id = $1",
            task_id,
        )

    async def end_session(self, session_id: str, was_completed: bool, was_aborted: bool) -> dict:
        async with get_connection() as connection:
            return await self.end_session_tx(
                connection,
                session_id=session_id,
                was_completed=was_completed,
                was_aborted=was_aborted,
            )