from app.infrastructure.db.connection import get_connection


def _serialize_subject(record) -> dict | None:
    if record is None:
        return None

    return {
        "id": record["id"],
        "name": record["name"],
        "color": record["color"],
        "icon": record["icon"],
    }


class SubjectRepository:
    async def list_subjects(self) -> list[dict]:
        query = """
            SELECT id, name, color, icon
            FROM subjects
            ORDER BY name ASC
        """

        async with get_connection() as connection:
            records = await connection.fetch(query)

        return [_serialize_subject(record) for record in records]