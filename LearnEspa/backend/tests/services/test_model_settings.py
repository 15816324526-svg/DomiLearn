from __future__ import annotations

import json

import httpx
import pytest

from app.services.deepseek_client import DeepSeekClient, official_base_url
from app.services.import_service import ServiceError
from app.services.model_settings import ModelConfig, ModelSettingsStore


class FakeSecretStore:
    def encrypt(self, value: str) -> str:
        return "encrypted:" + value[::-1]

    def decrypt(self, value: str) -> str:
        return value.removeprefix("encrypted:")[::-1]


def client_for(tmp_path, handler):
    store = ModelSettingsStore(tmp_path, FakeSecretStore())
    client = DeepSeekClient(store, httpx.Client(transport=httpx.MockTransport(handler)))
    return store, client


def success_response() -> httpx.Response:
    return httpx.Response(200, json={
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"ok": True})}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11},
    })


def test_only_official_https_destination_receives_key(tmp_path):
    called = []

    def handler(request):
        called.append(request.url)
        return success_response()

    store, client = client_for(tmp_path, handler)
    for url in ("http://api.deepseek.com", "https://api.deepseek.com.evil.test", "https://evil.test", "https://api.deepseek.com/redirect"):
        with pytest.raises(ServiceError) as error:
            client.probe_and_activate("test-model", url, "sk-new")
        assert error.value.status_code == 400
    assert called == []
    assert official_base_url("https://api.deepseek.com/v1/") == "https://api.deepseek.com/v1"
    assert client.probe_and_activate("test-model", "https://api.deepseek.com", "sk-new")["has_api_key"]
    assert str(called[0]) == "https://api.deepseek.com/chat/completions"
    assert "sk-new" not in store.path.read_text(encoding="utf-8")
    assert "sk-new" not in json.dumps(store.get_public())


def test_failed_probe_and_failed_save_preserve_old_active_config(tmp_path, monkeypatch):
    responses = [success_response(), httpx.Response(401), success_response()]
    store, client = client_for(tmp_path, lambda _request: responses.pop(0))
    client.probe_and_activate("old-model", "https://api.deepseek.com", "old-key")
    with pytest.raises(ServiceError) as denied:
        client.probe_and_activate("new-model", "https://api.deepseek.com", "bad-key")
    assert denied.value.status_code == 401
    assert store.get_active().model_id == "old-model"
    assert store.get_active().api_key == "old-key"

    def fail_replace(_source, _target):
        raise OSError("disk not writable")

    monkeypatch.setattr("app.services.model_settings.os.replace", fail_replace)
    with pytest.raises(ServiceError) as save_error:
        client.probe_and_activate("new-model", "https://api.deepseek.com", "new-key")
    assert save_error.value.code == "KEY_STORAGE_FAILED"
    assert store.get_active().model_id == "old-model"
    assert store.get_active().api_key == "old-key"


def test_structured_call_maps_usage_and_rejects_invalid_json(tmp_path):
    responses = [success_response(), httpx.Response(200, json={
        "choices": [{"finish_reason": "stop", "message": {"content": "{not-json"}}],
    })]
    store, client = client_for(tmp_path, lambda _request: responses.pop(0))
    store.activate(ModelConfig("test-model", "https://api.deepseek.com", "secret"))
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False}
    result, usage = client.generate_structured("test", "Return JSON", "ok", schema)
    assert result == {"ok": True}
    assert usage == {"purpose": "test", "input_tokens": 8, "output_tokens": 3, "total_tokens": 11}
    with pytest.raises(ServiceError) as invalid:
        client.generate_structured("test", "Return JSON", "ok", schema)
    assert invalid.value.code == "MODEL_RESPONSE_INVALID"
