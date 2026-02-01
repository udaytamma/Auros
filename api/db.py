from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase
from pathlib import Path

from alembic import command
from alembic.config import Config

from .config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    _run_migrations()


def _run_migrations() -> None:
    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    alembic_cfg = Config(str(config_path))
    alembic_cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    url = settings.DATABASE_URL
    if url.startswith("sqlite+aiosqlite"):
        url = url.replace("sqlite+aiosqlite", "sqlite", 1)
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    try:
        command.upgrade(alembic_cfg, "head")
    except OperationalError as exc:
        # Handle legacy DBs created via metadata.create_all()
        if "already exists" not in str(exc).lower():
            raise
        sync_engine = create_engine(url, future=True)
        from .models import Base as ModelBase  # noqa: WPS433

        ModelBase.metadata.create_all(sync_engine)
        command.stamp(alembic_cfg, "head")


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
