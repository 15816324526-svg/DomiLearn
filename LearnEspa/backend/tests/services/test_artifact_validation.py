import json

import pytest

from app.converters.base import InvalidArtifacts
from app.services.artifact_validation import validate_artifacts


def test_valid_artifacts_return_real_page_count(tmp_path) -> None:
    markdown = tmp_path / "document.md"
    document_json = tmp_path / "document.json"
    markdown.write_text("# 教材", encoding="utf-8")
    document_json.write_text(json.dumps({"pages": {"1": {}, "2": {}}}), encoding="utf-8")
    assert validate_artifacts(markdown, document_json, 2) == 2


@pytest.mark.parametrize("case", ["missing_md", "empty_md", "missing_json", "bad_json", "no_pages", "wrong_pages"])
def test_invalid_artifacts_are_rejected(tmp_path, case: str) -> None:
    markdown = tmp_path / "document.md"
    document_json = tmp_path / "document.json"
    if case != "missing_md":
        markdown.write_text("" if case == "empty_md" else "# 教材", encoding="utf-8")
    if case not in ("missing_json",):
        payload = {
            "bad_json": "{",
            "no_pages": json.dumps({"name": "book"}),
            "wrong_pages": json.dumps({"pages": {"1": {}}}),
        }.get(case, json.dumps({"pages": {"1": {}, "2": {}}}))
        document_json.write_text(payload, encoding="utf-8")

    with pytest.raises(InvalidArtifacts):
        validate_artifacts(markdown, document_json, 2)
