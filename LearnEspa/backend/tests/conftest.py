from pathlib import Path

import pytest

from app.core.config import Settings
from app.db.session import create_engine_from_settings, initialize_database, make_session_factory


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    storage = tmp_path / "storage"
    settings = Settings(
        storage_root=storage,
        database_url=f"sqlite:///{(storage / 'test.db').as_posix()}",
        converter="fake",
    )
    settings.ensure_directories()
    return settings


@pytest.fixture
def session_factory(test_settings: Settings):
    engine = create_engine_from_settings(test_settings)
    initialize_database(engine)
    return make_session_factory(engine)

