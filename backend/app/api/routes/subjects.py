from fastapi import APIRouter, HTTPException, status

from app.api.schemas.subjects import SubjectResponse
from app.domain.services.subject_service import SubjectService
from app.infrastructure.db.connection import DatabaseUnavailableError
from app.infrastructure.repositories.subject_repository import SubjectRepository


router = APIRouter()

subject_service = SubjectService(subject_repository=SubjectRepository())


@router.get("/subjects", response_model=list[SubjectResponse], status_code=status.HTTP_200_OK)
async def list_subjects() -> list[SubjectResponse]:
    try:
        return await subject_service.list_subjects()
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service temporarily unavailable.") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve subjects.") from exc