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


class SessionRepository:
    async def get_open_session_for_task(self, task_id: str) -> dict | None:
        query = """
            SELECT id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes,
                   actual_duration_minutes, was_completed, was_aborted
            FROM sessions
            WHERE task_id = $1 AND ended_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
        """

        async with get_connection() as connection:
            record = await connection.fetchrow(query, task_id)

        return _serialize_session(record)

    async def create_session(self, task_id: str, subtask_id: str | None, planned_duration_minutes: int) -> dict:
        query = """
            INSERT INTO sessions (task_id, subtask_id, planned_duration_minutes)
            VALUES ($1, $2, $3)
            RETURNING id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes,
                      actual_duration_minutes, was_completed, was_aborted
        """

        async with get_connection() as connection:
            record = await connection.fetchrow(query, task_id, subtask_id, planned_duration_minutes)

        return _serialize_session(record)

    async def get_session(self, session_id: str) -> dict | None:
        query = """
            SELECT id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes,
                   actual_duration_minutes, was_completed, was_aborted
            FROM sessions
            WHERE id = $1
        """

        async with get_connection() as connection:
            record = await connection.fetchrow(query, session_id)

        return _serialize_session(record)

    async def end_session(self, session_id: str, was_completed: bool, was_aborted: bool) -> dict:
        query = """
            UPDATE sessions
            SET ended_at = NOW(),
                was_completed = $2,
                was_aborted = $3
            WHERE id = $1
            RETURNING id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes,
                      actual_duration_minutes, was_completed, was_aborted
        """

        async with get_connection() as connection:
            record = await connection.fetchrow(query, session_id, was_completed, was_aborted)

        return _serialize_session(record)