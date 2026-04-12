from app.infrastructure.db.connection import get_connection


def _serialize_task(record) -> dict | None:
    if record is None:
        return None

    return {
        "id": record["id"],
        "title": record["title"],
        "subject_id": record["subject_id"],
        "created_at": record["created_at"],
        "is_completed": record["is_completed"],
    }


def _serialize_task_candidate(record) -> dict:
    return {
        "id": record["id"],
        "title": record["title"],
        "subject_id": record["subject_id"],
        "created_at": record["created_at"],
        "is_completed": record["is_completed"],
        "latest_ended_at": record["latest_ended_at"],
        "latest_ended_was_aborted": record["latest_ended_was_aborted"],
        "latest_started_at": record["latest_started_at"],
        "ended_abort_count": record["ended_abort_count"],
        "has_session_history": record["has_session_history"],
    }


class TaskRepository:
    async def create_task(self, title: str, subject_id: str | None = None) -> dict:
        query = """
            INSERT INTO tasks (title, subject_id)
            VALUES ($1, $2)
            RETURNING id, title, subject_id, created_at, is_completed
        """

        async with get_connection() as connection:
            record = await connection.fetchrow(query, title, subject_id)

        return _serialize_task(record)

    async def list_tasks(self) -> list[dict]:
        query = """
            SELECT id, title, subject_id, created_at, is_completed
            FROM tasks
            ORDER BY created_at DESC
        """

        async with get_connection() as connection:
            records = await connection.fetch(query)

        return [_serialize_task(record) for record in records]

    async def get_task(self, task_id: str) -> dict | None:
        query = """
            SELECT id, title, subject_id, created_at, is_completed
            FROM tasks
            WHERE id = $1
        """

        async with get_connection() as connection:
            record = await connection.fetchrow(query, task_id)

        return _serialize_task(record)

    async def get_next_task_candidates(self) -> list[dict]:
        query = """
            SELECT t.id,
                   t.title,
                   t.subject_id,
                   t.created_at,
                   t.is_completed,
                   latest_ended.ended_at AS latest_ended_at,
                   latest_ended.was_aborted AS latest_ended_was_aborted,
                   latest_started.started_at AS latest_started_at,
                   COALESCE(aborted_sessions.ended_abort_count, 0) AS ended_abort_count,
                   EXISTS(
                       SELECT 1
                       FROM sessions session_history
                       WHERE session_history.task_id = t.id
                         AND session_history.ended_at IS NOT NULL
                   ) AS has_session_history
            FROM tasks t
            LEFT JOIN LATERAL (
                SELECT s.ended_at, s.was_aborted
                FROM sessions s
                WHERE s.task_id = t.id AND s.ended_at IS NOT NULL
                ORDER BY s.ended_at DESC
                LIMIT 1
            ) AS latest_ended ON TRUE
            LEFT JOIN LATERAL (
                SELECT s.started_at
                FROM sessions s
                WHERE s.task_id = t.id
                ORDER BY s.started_at DESC
                LIMIT 1
            ) AS latest_started ON TRUE
            LEFT JOIN LATERAL (
                SELECT COUNT(*)::int AS ended_abort_count
                FROM sessions s
                WHERE s.task_id = t.id
                  AND s.ended_at IS NOT NULL
                  AND s.was_aborted = TRUE
            ) AS aborted_sessions ON TRUE
            WHERE t.is_completed = FALSE
        """

        async with get_connection() as connection:
            records = await connection.fetch(query)

        return [_serialize_task_candidate(record) for record in records]