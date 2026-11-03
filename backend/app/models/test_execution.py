import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.code_patch import CodePatch


class TestExecutionStatus(str, enum.Enum):
    __test__ = False
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TestExecution(Base):
    __test__ = False
    __tablename__ = "test_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    patch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("code_patches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[TestExecutionStatus] = mapped_column(
        Enum(TestExecutionStatus, name="test_execution_status", native_enum=False),
        default=TestExecutionStatus.PENDING,
        nullable=False,
        index=True,
    )
    execution_environment: Mapped[str] = mapped_column(
        String(100),
        default="docker_sandbox",
        nullable=False,
    )
    command_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    output_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    exit_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    patch: Mapped["CodePatch"] = relationship(
        "CodePatch",
        back_populates="test_executions",
    )

