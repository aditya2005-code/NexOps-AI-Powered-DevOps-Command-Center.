from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import JSON
from sqlalchemy.dialects.postgresql import JSONB

# Portable JSON type: native JSONB on PostgreSQL, standard JSON on SQLite
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    """Central declarative base for all NexOps SQLAlchemy models."""
    pass


# Ensure all models are registered on Base.metadata for Alembic autogeneration
import app.models  # noqa: F401, E402
