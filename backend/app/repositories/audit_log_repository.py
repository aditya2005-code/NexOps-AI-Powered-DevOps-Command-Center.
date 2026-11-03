import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate


class AuditLogRepository:
    """Append-only audit log repository ensuring traceability of actions and decisions."""

    @staticmethod
    def append(db: Session, log_in: AuditLogCreate) -> AuditLog:
        log = AuditLog(
            actor_type=log_in.actor_type,
            actor_identifier=log_in.actor_identifier,
            action=log_in.action,
            resource_type=log_in.resource_type,
            resource_id=log_in.resource_id,
            details=log_in.details,
        )
        db.add(log)
        db.flush()
        return log

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        statement = select(AuditLog).offset(skip).limit(limit).order_by(AuditLog.created_at.desc())
        return list(db.scalars(statement).all())

    @staticmethod
    def get_by_resource(
        db: Session,
        resource_type: str,
        resource_id: Optional[uuid.UUID] = None,
    ) -> List[AuditLog]:
        statement = select(AuditLog).where(AuditLog.resource_type == resource_type)
        if resource_id is not None:
            statement = statement.where(AuditLog.resource_id == resource_id)
        statement = statement.order_by(AuditLog.created_at.desc())
        return list(db.scalars(statement).all())

