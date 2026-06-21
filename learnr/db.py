import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    db_path = os.environ.get("LEARNR_DB_PATH", "learnr.sqlite3")
    if db_path == ":memory:":
        return "sqlite+pysqlite:///:memory:"
    return f"sqlite+pysqlite:///{Path(db_path).expanduser().resolve()}"


engine = create_engine(
    database_url(),
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def register_models() -> None:
    # Importing model modules registers their tables on Base.metadata before create_all().
    from learnr import models  # noqa: F401


def init_db() -> None:
    register_models()
    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session]:
    with SessionLocal() as session:
        yield session
