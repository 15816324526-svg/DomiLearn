from __future__ import annotations

import json
from pathlib import Path

from app.converters.base import InvalidArtifacts


def validate_artifacts(markdown_path: Path, json_path: Path, expected_pages: int) -> int:
    if not markdown_path.is_file() or not markdown_path.read_text(encoding="utf-8").strip():
        raise InvalidArtifacts("Markdown 输出缺失或为空")
    if not json_path.is_file():
        raise InvalidArtifacts("JSON 输出缺失")
    try:
        document = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidArtifacts("JSON 输出无法读取") from exc
    pages = document.get("pages")
    if not isinstance(pages, dict):
        raise InvalidArtifacts("JSON 输出缺少页面信息")
    if len(pages) != expected_pages:
        raise InvalidArtifacts(f"页面数量不一致：期望 {expected_pages}，实际 {len(pages)}")
    return len(pages)

