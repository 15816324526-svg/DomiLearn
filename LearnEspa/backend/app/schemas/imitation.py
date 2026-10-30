from __future__ import annotations

from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=100)
    answer: str = Field(min_length=1, max_length=5000)
    source_mode: str
    hint_viewed: bool = False


class DraftRequest(BaseModel):
    text: str = Field(max_length=5000)


class NextRequest(BaseModel):
    manual_pass: bool = False


class PreferenceRequest(BaseModel):
    default_source_mode: str
