import logging
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("nexops.database")

_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker[Session]] = None


def get_engine() -> Engine:
    """Lazily initialize and return the SQLAlchemy database engine with connection pooling."""
    global _engine
    if _engine is None:
        db_url = settings.sqlalchemy_database_url
        is_sqlite = db_url.startswith("sqlite")

        engine_kwargs = {
            "echo": settings.DATABASE_ECHO,
        }

        # Apply connection pooling options for client-server databases like PostgreSQL
        if not is_sqlite:
            engine_kwargs.update({
                "pool_size": settings.DATABASE_POOL_SIZE,
                "max_overflow": settings.DATABASE_MAX_OVERFLOW,
                "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
                "pool_recycle": settings.DATABASE_POOL_RECYCLE,
                "pool_pre_ping": True,
            })

        _engine = create_engine(db_url, **engine_kwargs)
        logger.info("Initialized database engine with dialect: %s", _engine.dialect.name)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the cached SessionLocal session factory."""
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            expire_on_commit=False,
        )
    return _SessionFactory


def SessionLocal() -> Session:
    """Helper to instantiate a new database session."""
    factory = get_session_factory()
    return factory()
