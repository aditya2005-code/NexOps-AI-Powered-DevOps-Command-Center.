import hashlib
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.agent_execution import AgentExecution
    from app.models.approval import Approval
    from app.models.test_execution import TestExecution


class CodePatch(Base):
    __tablename__ = "code_patches"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("agent_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    patch_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    patch_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    base_commit: Mapped[Optional[str]] = mapped_column(
        String(40),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending_approval",
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @staticmethod
    def compute_sha256(content: str) -> str:
        """Compute cryptographic SHA-256 hash of patch content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Relationships
    incident: Mapped["Incident"] = relationship(
        "Incident",
        back_populates="code_patches",
    )
    agent_execution: Mapped[Optional["AgentExecution"]] = relationship(
        "AgentExecution",
        back_populates="code_patches",
    )
    approvals: Mapped[List["Approval"]] = relationship(
        "Approval",
        back_populates="patch",
        cascade="all, delete-orphan",
    )
    test_executions: Mapped[List["TestExecution"]] = relationship(
        "TestExecution",
        back_populates="patch",
        cascade="all, delete-orphan",
    )

