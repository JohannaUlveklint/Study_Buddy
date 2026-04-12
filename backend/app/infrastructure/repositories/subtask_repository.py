from app.infrastructure.db.connection import get_connection


def _serialize_subtask(record) -> dict | None:
    if record is None:
        return None

    return {
        "id": record["id"],
        "task_id": record["task_id"],
        "title": record["title"],
        "difficulty_level": record["difficulty_level"],
        "is_completed": record["is_completed"],
    }


class SubtaskRepository:
    async def create_subtask(
        self,
        task_id: str,
        title: str,
        difficulty_level: int,
        connection=None,
    ) -> dict:
        query = """
            INSERT INTO subtasks (task_id, title, difficulty_level)
            VALUES ($1, $2, $3)
            RETURNING id, task_id, title, difficulty_level, is_completed
        """

        if connection is not None:
            record = await connection.fetchrow(query, task_id, title, difficulty_level)
            return _serialize_subtask(record)

        async with get_connection() as db_connection:
            record = await db_connection.fetchrow(query, task_id, title, difficulty_level)

        return _serialize_subtask(record)