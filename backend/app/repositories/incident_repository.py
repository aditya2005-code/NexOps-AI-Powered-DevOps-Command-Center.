import uuid
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.models.incident_event import IncidentEvent
from app.schemas.incident import IncidentCreate, IncidentEventCreate


class IncidentRepository:
    """Repository handling persistence operations for Incidents and Incident Events."""

    @staticmethod
    def create(db: Session, incident_in: IncidentCreate) -> Incident:
        incident = Incident(
            project_id=incident_in.project_id,
            title=incident_in.title,
            description=incident_in.description,
            severity=incident_in.severity,
            status=incident_in.status,
            source=incident_in.source,
            source_id=incident_in.source_id,
            root_cause_summary=incident_in.root_cause_summary,
        )
        db.add(incident)
        db.flush()
        return incident

    @staticmethod
    def get_by_id(db: Session, incident_id: uuid.UUID) -> Optional[Incident]:
        statement = select(Incident).where(Incident.id == incident_id)
        return db.scalar(statement)

    @staticmethod
    def get_by_source_id(db: Session, source_id: str) -> Optional[Incident]:
        statement = select(Incident).where(Incident.source_id == source_id)
        return db.scalar(statement)

    @staticmethod
    def list(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[IncidentStatus] = None,
        severity: Optional[IncidentSeverity] = None,
        project_id: Optional[uuid.UUID] = None,
    ) -> List[Incident]:
        statement = select(Incident)
        if status is not None:
            statement = statement.where(Incident.status == status)
        if severity is not None:
            statement = statement.where(Incident.severity == severity)
        if project_id is not None:
            statement = statement.where(Incident.project_id == project_id)
        statement = statement.offset(skip).limit(limit).order_by(Incident.detected_at.desc())
        return list(db.scalars(statement).all())

    @staticmethod
    def count(db: Session, status: Optional[IncidentStatus] = None) -> int:
        statement = select(func.count(Incident.id))
        if status is not None:
            statement = statement.where(Incident.status == status)
        return db.scalar(statement) or 0

    @staticmethod
    def update_status(db: Session, incident: Incident, status: IncidentStatus) -> Incident:
        incident.status = status
        db.flush()
        return incident

    @staticmethod
    def list_by_project(db: Session, project_id: uuid.UUID) -> List[Incident]:
        statement = select(Incident).where(Incident.project_id == project_id).order_by(Incident.detected_at.desc())
        return list(db.scalars(statement).all())

    @staticmethod
    def list_by_severity(db: Session, severity: IncidentSeverity) -> List[Incident]:
        statement = select(Incident).where(Incident.severity == severity).order_by(Incident.detected_at.desc())
        return list(db.scalars(statement).all())

    @staticmethod
    def create_event(db: Session, event_in: IncidentEventCreate) -> IncidentEvent:
        event = IncidentEvent(
            incident_id=event_in.incident_id,
            event_type=event_in.event_type,
            actor_type=event_in.actor_type,
            actor_identifier=event_in.actor_identifier,
            description=event_in.description,
            event_metadata=event_in.event_metadata,
        )
        db.add(event)
        db.flush()
        return event

    @staticmethod
    def list_events_by_incident(db: Session, incident_id: uuid.UUID) -> List[IncidentEvent]:
        statement = select(IncidentEvent).where(IncidentEvent.incident_id == incident_id).order_by(IncidentEvent.created_at.asc())
        return list(db.scalars(statement).all())

