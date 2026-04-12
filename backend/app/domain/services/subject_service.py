from app.infrastructure.repositories.subject_repository import SubjectRepository


class SubjectService:
    def __init__(self, subject_repository: SubjectRepository) -> None:
        self._subject_repository = subject_repository

    async def list_subjects(self) -> list[dict]:
        return await self._subject_repository.list_subjects()