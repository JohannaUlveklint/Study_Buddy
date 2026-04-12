from uuid import UUID

from pydantic import BaseModel


class SubjectResponse(BaseModel):
    id: UUID
    name: str
    color: str
    icon: str