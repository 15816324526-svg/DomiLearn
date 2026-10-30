from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.textbook_imports import envelope
from app.schemas.model_settings import ModelSettingsTestRequest
from app.services.deepseek_client import DeepSeekClient


router = APIRouter(prefix="/api/model-settings", tags=["model-settings"])


def _client(request: Request) -> DeepSeekClient:
    return request.app.state.model_client


@router.get("")
def get_model_settings(request: Request) -> dict:
    return envelope(_client(request).settings_store.get_public())


@router.post("/test")
def test_model_settings(payload: ModelSettingsTestRequest, request: Request) -> dict:
    public = _client(request).probe_and_activate(payload.model_id, payload.url, payload.api_key)
    return envelope(public, "测试成功，服务可用")

#model_settings.py提供两个接口：
#GET  /api/model-settings
#POST /api/model-settings/test