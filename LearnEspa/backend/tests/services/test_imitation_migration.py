from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.config import BACKEND_ROOT
from app.db.session import create_engine_from_settings


def test_existing_vocabulary_database_upgrades_without_dropping_history(test_settings):
    engine = create_engine_from_settings(test_settings)
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0003_vocabulary_session")
    before = set(inspect(engine).get_table_names())
    assert {"vocabulary_sessions", "vocabulary_attempts"} <= before
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0004_imitation")
    assert "core_pattern" not in {column["name"] for column in inspect(engine).get_columns("passage_sentences")}
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    after = set(inspect(engine).get_table_names())
    assert before <= after
    assert {"passage_sentences", "imitation_rounds", "imitation_attempts", "imitation_reports"} <= after
    assert {"core_pattern", "fixed_collocations_json"} <= {
        column["name"] for column in inspect(engine).get_columns("passage_sentences")
    }
