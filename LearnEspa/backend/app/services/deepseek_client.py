"""Official DeepSeek chat-completions client for structured JSON tasks."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.services.import_service import ServiceError
from app.services.model_settings import ModelConfig, ModelSettingsStore


def official_base_url(value: str) -> str:
    try:
        parsed = urlsplit(value.strip())
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ServiceError("MODEL_PROVIDER_UNSUPPORTED", 400, "模型服务 URL 格式无效") from exc
    if (
        parsed.scheme != "https" or hostname != "api.deepseek.com"
        or parsed.username or parsed.password or port not in (None, 443)
        or parsed.path not in ("", "/", "/v1", "/v1/")
        or parsed.query or parsed.fragment
    ):
        raise ServiceError("MODEL_PROVIDER_UNSUPPORTED", 400, "1.0 仅支持 DeepSeek 官方 API 地址 https://api.deepseek.com")
    return "https://api.deepseek.com/v1" if parsed.path.startswith("/v1") else "https://api.deepseek.com"


def _matches_schema(value: Any, schema: dict) -> bool:
    kind = schema.get("type")
    if isinstance(kind, list):
        return any(_matches_schema(value, {**schema, "type": item}) for item in kind)
    if kind == "object":
        if not isinstance(value, dict):
            return False
        properties = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", [])):
            return False
        if schema.get("additionalProperties") is False and any(key not in properties for key in value):
            return False
        return all(_matches_schema(item, properties[key]) for key, item in value.items() if key in properties)
    if kind == "array":
        return isinstance(value, list) and all(_matches_schema(item, schema.get("items", {})) for item in value)
    if kind == "string":
        return isinstance(value, str) and ("enum" not in schema or value in schema["enum"])
    if kind == "boolean":
        return type(value) is bool
    if kind == "integer":
        return type(value) is int
    if kind == "null":
        return value is None
    return True


_UPSTREAM_ERRORS = {
    400: "模型服务拒绝了请求，请检查 Model ID 与请求格式",
    401: "API Key 无效或无权访问该模型",
    402: "模型服务账户余额不足",
    403: "模型服务拒绝访问，请检查账户权限",
    404: "模型服务地址或 Model ID 不存在",
    422: "模型服务无法处理该请求，请检查 Model ID",
    429: "模型服务请求过于频繁，请稍后重试",
    500: "模型服务内部错误，请稍后重试",
    502: "模型服务网关错误，请稍后重试",
    503: "模型服务暂时不可用，请稍后重试",
    504: "模型服务响应超时，请稍后重试",
}


class DeepSeekClient:
    def __init__(self, settings_store: ModelSettingsStore, http_client: httpx.Client | None = None) -> None:
        self.settings_store = settings_store
        self.http_client = http_client or httpx.Client(timeout=httpx.Timeout(120.0, connect=15.0))

    def _request(self, config: ModelConfig, purpose: str, system_prompt: str, user_prompt: str, schema: dict) -> tuple[dict, dict | None]:
        base = official_base_url(config.url)
        token_limit = 8192 if purpose in ("imitation_plan", "imitation_compose", "imitation_repair") else 3072
        payload = {
            "model": config.model_id,
            "messages": [
                {"role": "system", "content": system_prompt + "\n请只输出一个有效 JSON 对象，严格遵守用户消息所给 JSON Schema，不要 Markdown。"},
                {"role": "user", "content": user_prompt + "\n\nJSON Schema:\n" + json.dumps(schema, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": token_limit,
            "stream": False,
        }
        try:
            response = self.http_client.post(
                base + "/chat/completions",
                headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise ServiceError("MODEL_TIMEOUT", 504, "连接模型超时（无服务方 HTTP 状态码），可重试") from exc
        except httpx.RequestError as exc:
            raise ServiceError("MODEL_NETWORK_ERROR", 502, "无法连接模型服务（无服务方 HTTP 状态码），请检查网络") from exc
        if not response.is_success:
            status = response.status_code
            message = _UPSTREAM_ERRORS.get(status, "模型服务返回错误，请稍后重试")
            raise ServiceError(f"MODEL_HTTP_{status}", status, f"模型服务 HTTP {status}：{message}")
        try:
            body = response.json()
            choice = body["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ValueError("incomplete model output")
            content = choice["message"]["content"]
            result = json.loads(content)
            if not _matches_schema(result, schema):
                raise ValueError("schema mismatch")
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "模型回复不完整或格式异常，请重试") from exc
        usage = body.get("usage")
        normalized_usage = None
        if isinstance(usage, dict):
            normalized_usage = {
                "purpose": purpose,
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
            }
        return result, normalized_usage

    def generate_structured(self, purpose: str, system_prompt: str, user_prompt: str, schema: dict) -> tuple[dict, dict | None]:
        return self._request(self.settings_store.get_active(), purpose, system_prompt, user_prompt, schema)

    def probe_and_activate(self, model_id: str, url: str, api_key: str) -> dict:
        model_id = model_id.strip()
        api_key = api_key.strip()
        if not model_id or not api_key:
            raise ServiceError("MODEL_SETTINGS_INCOMPLETE", 400, "请填写 Model ID、URL 和 API Key")
        normalized_url = official_base_url(url)
        candidate = ModelConfig(model_id=model_id, url=normalized_url, api_key=api_key)
        schema = {
            "type": "object", "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"], "additionalProperties": False,
        }
        result, _usage = self._request(candidate, "connection_probe", "你是连接测试。请只输出 JSON：{\"ok\":true}。", "返回 ok=true。", schema)
        if result.get("ok") is not True:
            raise ServiceError("MODEL_PROBE_FAILED", 502, "模型没有通过结构化回复测试，旧服务仍可使用")
        return self.settings_store.activate(candidate)
