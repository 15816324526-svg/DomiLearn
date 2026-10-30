"""Windows-local model credentials with atomic replacement after a probe."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.services.import_service import ServiceError


@dataclass(frozen=True)
class ModelConfig:
    model_id: str
    url: str
    api_key: str


class WindowsDpapiSecretStore:
    def encrypt(self, secret: str) -> str:
        try:
            import win32crypt
            ciphertext = win32crypt.CryptProtectData(secret.encode("utf-8"), "DomiLearn API Key", None, None, None, 0)
        except Exception as exc:
            raise ServiceError("KEY_STORAGE_FAILED", 500, "无法在本机安全保存 API Key") from exc
        return base64.b64encode(ciphertext).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        try:
            import win32crypt
            _description, plaintext = win32crypt.CryptUnprotectData(base64.b64decode(ciphertext), None, None, None, 0)
            return plaintext.decode("utf-8")
        except Exception as exc:
            raise ServiceError("KEY_UNAVAILABLE", 500, "已保存的 API Key 无法在当前 Windows 账户读取") from exc


class ModelSettingsStore:
    def __init__(self, storage_root: Path, secret_store=None) -> None:
        self.path = storage_root / "settings" / "model-service.json"
        self.secret_store = secret_store or WindowsDpapiSecretStore()
        self.lock = Lock()

    def _read(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("not an object")
            return document
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ServiceError("MODEL_SETTINGS_CORRUPT", 500, "本机模型设置无法读取") from exc

    def get_public(self) -> dict:
        document = self._read()
        return {
            "model_id": document.get("model_id", "") if document else "",
            "url": document.get("url", "") if document else "",
            "has_api_key": bool(document and document.get("encrypted_api_key")),
        }

    def get_active(self) -> ModelConfig:
        document = self._read()
        if not document or not document.get("encrypted_api_key"):
            raise ServiceError("MODEL_NOT_CONFIGURED", 409, "请先在仪表盘设置并测试模型服务")
        return ModelConfig(
            model_id=str(document["model_id"]), url=str(document["url"]),
            api_key=self.secret_store.decrypt(str(document["encrypted_api_key"])),
        )

    def activate(self, config: ModelConfig) -> dict:
        encrypted_key = self.secret_store.encrypt(config.api_key)
        document = {
            "model_id": config.model_id, "url": config.url,
            "encrypted_api_key": encrypted_key,
        }
        body = json.dumps(document, ensure_ascii=False).encode("utf-8")
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_name(f".{self.path.name}.{uuid4().hex}.tmp")
            try:
                with open(temp, "xb") as stream:
                    stream.write(body)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp, self.path)
            except OSError as exc:
                raise ServiceError("KEY_STORAGE_FAILED", 500, "模型连接成功，但无法保存新设置；旧服务仍可使用") from exc
            finally:
                temp.unlink(missing_ok=True)
        return self.get_public()
