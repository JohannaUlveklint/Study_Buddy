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