from app.infrastructure.db.connection import get_connection


def _serialize_attempt(record) -> dict | None:
    if record is None:
        return None

    return {
        "id": record["id"],
        "session_id": record["session_id"],
        "difficulty_level": record["difficulty_level"],
        "outcome": record["outcome"],
    }


class AttemptRepository:
    async def create_attempt(self, conn, session_id: str, outcome: str) -> dict | None:
        query = """
            INSERT INTO attempts (session_id, difficulty_level, outcome)
            SELECT s.id, st.difficulty_level, $2
            FROM sessions s
            JOIN subtasks st ON st.id = s.subtask_id
            WHERE s.id = $1
            RETURNING id, session_id, difficulty_level, outcome
        """

        record = await conn.fetchrow(query, session_id, outcome)

        return _serialize_attempt(record)

    async def get_recent_attempts(self, task_id: str, limit: int = 5) -> list[dict]:
        query = """
            SELECT a.id, a.session_id, a.difficulty_level, a.outcome
            FROM attempts a
            JOIN sessions s ON s.id = a.session_id
            WHERE s.task_id = $1
            ORDER BY s.ended_at DESC NULLS LAST, a.id DESC
            LIMIT $2
        """

        async with get_connection() as connection:
            records = await connection.fetch(query, task_id, limit)

        return [_serialize_attempt(record) for record in records]