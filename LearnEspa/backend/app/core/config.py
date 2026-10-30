from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOMILEARN_",
        env_file=BACKEND_ROOT / ".env",
        extra="ignore",
    )

    storage_root: Path = BACKEND_ROOT / "storage"
    database_url: str = f"sqlite:///{(BACKEND_ROOT / 'storage' / 'domilearn.db').as_posix()}"
    max_pdf_bytes: int = 500 * 1024 * 1024
    conversion_timeout_seconds: int = 2 * 60 * 60
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    worker_poll_seconds: float = 1.0
    converter: str = "docling"

    def ensure_directories(self) -> None:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        (self.storage_root / ".tmp" / "uploads").mkdir(parents=True, exist_ok=True)
        (self.storage_root / ".tmp" / "conversions").mkdir(parents=True, exist_ok=True)
        (self.storage_root / "logs" / "jobs").mkdir(parents=True, exist_ok=True)
        textbook_root = self.storage_root / "textbooks" / "modern-spanish-1"
        (textbook_root / "originals").mkdir(parents=True, exist_ok=True)
        (textbook_root / "conversions").mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()

