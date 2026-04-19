from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


def error_response(description: str) -> dict:
    return {
        "model": ErrorResponse,
        "description": description,
    }