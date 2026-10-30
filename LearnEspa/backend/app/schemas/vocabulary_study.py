from __future__ import annotations

from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    session_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1, max_length=36)
    answer: str | int | None


class NextRequest(BaseModel):
    session_id: str = Field(min_length=1)
