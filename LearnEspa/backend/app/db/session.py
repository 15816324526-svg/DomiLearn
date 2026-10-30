from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import BACKEND_ROOT, Settings, get_settings
from app.db.base import Base


def create_engine_from_settings(settings: Settings) -> Engine:
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, connect_args=connect_args)

    if settings.database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def initialize_database(engine: Engine) -> None:
    from app.models import Textbook

    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory.begin() as session:
        textbook = session.scalar(select(Textbook).where(Textbook.id == "modern-spanish-1"))
        if textbook is None:
            session.add(Textbook(id="modern-spanish-1", title="现代西班牙语1"))


def upgrade_database(engine: Engine) -> None:
    """Apply committed Alembic migrations using the application's engine."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


_engine = create_engine_from_settings(get_settings())
SessionLocal = make_session_factory(_engine)


@contextmanager
def session_scope(factory: sessionmaker[Session] = SessionLocal) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

