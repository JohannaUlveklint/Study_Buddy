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

    async def get_next_task(self) -> dict | None:
        query = """
            WITH latest_sessions AS (
                SELECT DISTINCT ON (s.task_id) s.task_id, s.ended_at, s.was_aborted
                FROM sessions s
                WHERE s.ended_at IS NOT NULL
                ORDER BY s.task_id, s.ended_at DESC
            )
            SELECT t.id, t.title, t.subject_id, t.created_at, t.is_completed
            FROM tasks t
            LEFT JOIN latest_sessions ls ON ls.task_id = t.id
            WHERE t.is_completed = FALSE
            ORDER BY CASE WHEN ls.was_aborted THEN 0 ELSE 1 END,
                     CASE WHEN ls.was_aborted THEN ls.ended_at END DESC NULLS LAST,
                     CASE WHEN ls.was_aborted THEN NULL ELSE t.created_at END ASC
            LIMIT 1
        """

        async with get_connection() as connection:
            record = await connection.fetchrow(query)

        return _serialize_task(record)