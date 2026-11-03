import logging
import uuid
from typing import Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.incident import IncidentSeverity, IncidentStatus
from app.repositories import (
    ProjectRepository,
    IncidentRepository,
    AuditLogRepository,
)
from app.schemas.incident import IncidentCreate, IncidentEventCreate
from app.schemas.audit_log import AuditLogCreate
from app.integrations.switch.client import SwitchClient
from app.integrations.switch.schemas import SwitchInboundEvent, SwitchIntakeResult

logger = logging.getLogger("nexops.switch.intake")


class SwitchIntakeService:
    """Service handling inbound Switch messages, mapping to projects, creating incidents and acknowledging."""

    def __init__(self, switch_client: Optional[SwitchClient] = None) -> None:
        self._switch_client = switch_client

    @staticmethod
    def compute_idempotency_key(room_id: str, message_id: str) -> str:
        """Compute collision-resistant composite idempotency key across Switch rooms and sources."""
        return f"switch:{room_id.strip()}:{message_id.strip()}"

    def _get_client(self) -> SwitchClient:
        """Resolve or lazily instantiate the SwitchClient."""
        if self._switch_client is not None:
            return self._switch_client
        core_url = settings.SWITCH_CORE_URL or "http://localhost:8080"
        api_key = settings.SWITCH_API_KEY or ""
        timeout = settings.SWITCH_CONNECTION_TIMEOUT
        return SwitchClient(core_url=core_url, api_key=api_key, timeout=timeout)

    async def process_inbound_event(
        self,
        event: SwitchInboundEvent,
        db: Optional[Session] = None,
    ) -> SwitchIntakeResult:
        """Process an inbound Switch event, persist incident transactionally, and acknowledge."""
        # 1. Validation of required identifiers and content limits
        if not event.room_id or not event.message_id or not event.content or not event.content.strip():
            logger.warning("Rejected invalid Switch event: missing room_id, message_id, or empty content")
            return SwitchIntakeResult(
                status="invalid_event",
                room_id=event.room_id,
                message_id=event.message_id,
                detail="Missing required message identifiers (room_id, message_id) or content is empty",
            )

        # Enforce reasonable payload length limit
        if len(event.content) > 10000:
            logger.warning("Rejected oversized Switch event: message exceeds 10,000 characters")
            return SwitchIntakeResult(
                status="invalid_event",
                room_id=event.room_id,
                message_id=event.message_id,
                detail="Message content exceeds maximum allowed length (10,000 chars)",
            )

        # Determine session lifecycle: external or managed local session
        managed_session = False
        if db is None:
            try:
                db = SessionLocal()
                managed_session = True
            except Exception as exc:
                logger.error("Database connection failure in Switch intake: %s", type(exc).__name__)
                return SwitchIntakeResult(
                    status="persistence_failure",
                    room_id=event.room_id,
                    message_id=event.message_id,
                    detail="Database unavailable",
                )

        try:
            return await self._process_with_session(event, db)
        except Exception as exc:
            logger.error("Unexpected error in Switch intake processing: %s", type(exc).__name__)
            try:
                db.rollback()
            except Exception:
                pass
            return SwitchIntakeResult(
                status="persistence_failure",
                room_id=event.room_id,
                message_id=event.message_id,
                detail=f"Persistence failed: {type(exc).__name__}",
            )
        finally:
            if managed_session and db is not None:
                db.close()

    async def _process_with_session(
        self,
        event: SwitchInboundEvent,
        db: Session,
    ) -> SwitchIntakeResult:
        """Execute transactional project lookup, idempotency verification, and incident creation."""
        room_id = event.room_id.strip()

        # 2. Map Room ID to Project Configuration
        mapping = settings.room_project_mapping
        mapped_target = mapping.get(room_id)

        if not mapped_target:
            logger.warning("Switch event from unmapped room '%s' rejected", room_id)
            self._record_audit(
                db=db,
                actor_identifier=event.sender_id or "switch_bridge",
                action="switch_room_unmapped_rejected",
                resource_type="switch_room",
                details={"room_id": room_id, "message_id": event.message_id},
            )
            db.commit()
            return SwitchIntakeResult(
                status="rejected_unmapped_room",
                room_id=room_id,
                message_id=event.message_id,
                detail=f"Room '{room_id}' is not mapped to any configured NexOps project",
            )

        # Look up project in database
        project = ProjectRepository.get_by_name(db, mapped_target)
        if project is None:
            # Check if mapped_target is a UUID string
            try:
                proj_uuid = uuid.UUID(mapped_target)
                project = ProjectRepository.get_by_id(db, proj_uuid)
            except (ValueError, TypeError):
                project = None

        if project is None:
            logger.warning(
                "Switch room '%s' mapped to target '%s' which does not exist in database",
                room_id,
                mapped_target,
            )
            self._record_audit(
                db=db,
                actor_identifier=event.sender_id or "switch_bridge",
                action="switch_room_unmapped_rejected",
                resource_type="switch_room",
                details={"room_id": room_id, "message_id": event.message_id, "target": mapped_target},
            )
            db.commit()
            return SwitchIntakeResult(
                status="rejected_unmapped_room",
                room_id=room_id,
                message_id=event.message_id,
                detail=f"Target project '{mapped_target}' does not exist",
            )

        # 3. Database-backed Idempotency Check (Composite Key)
        idempotency_key = self.compute_idempotency_key(room_id, event.message_id)
        existing_incident = IncidentRepository.get_by_source_id(db, idempotency_key)
        if existing_incident is not None:
            logger.info(
                "Duplicate Switch message '%s' (key: %s) detected. Returning existing incident #%s",
                event.message_id,
                idempotency_key,
                existing_incident.id,
            )
            self._record_audit(
                db=db,
                actor_identifier=event.sender_id or "switch_bridge",
                action="switch_message_duplicate_rejected",
                resource_type="incident",
                resource_id=existing_incident.id,
                details={"room_id": room_id, "message_id": event.message_id, "idempotency_key": idempotency_key},
            )
            db.commit()
            return SwitchIntakeResult(
                status="duplicate",
                incident_id=existing_incident.id,
                project_id=existing_incident.project_id,
                room_id=room_id,
                message_id=event.message_id,
                acknowledgement_sent=False,
                detail="Duplicate message already processed",
            )

        # 4. Create Incident, Event, and AuditLog Transactionally
        first_line = event.content.strip().split("\n")[0][:100]
        incident_title = f"Switch Incident: {first_line}"

        incident_in = IncidentCreate(
            project_id=project.id,
            title=incident_title,
            description=event.content,
            severity=IncidentSeverity.MEDIUM,
            status=IncidentStatus.OPEN,
            source="switch",
            source_id=idempotency_key,
        )

        try:
            incident = IncidentRepository.create(db, incident_in)

            # Persist original message as IncidentEvent
            event_in = IncidentEventCreate(
                incident_id=incident.id,
                event_type="switch_message",
                actor_type="switch_user",
                actor_identifier=event.sender_id or event.sender_name or "switch_user",
                description=event.content,
                event_metadata={
                    "room_id": room_id,
                    "message_id": event.message_id,
                    "thread_id": event.thread_id,
                    "sender_name": event.sender_name,
                },
            )
            IncidentRepository.create_event(db, event_in)

            # Record intake audit log
            self._record_audit(
                db=db,
                actor_identifier=event.sender_id or "switch_bridge",
                action="incident_created_via_switch",
                resource_type="incident",
                resource_id=incident.id,
                details={
                    "room_id": room_id,
                    "message_id": event.message_id,
                    "project_name": project.name,
                    "idempotency_key": idempotency_key,
                },
            )

            # Commit the transaction
            db.commit()
            db.refresh(incident)
        except IntegrityError:
            db.rollback()
            # Concurrent duplicate handled via database unique constraint
            existing = IncidentRepository.get_by_source_id(db, idempotency_key)
            if existing is not None:
                logger.info("Concurrent duplicate caught for message '%s' (key: %s)", event.message_id, idempotency_key)
                return SwitchIntakeResult(
                    status="duplicate",
                    incident_id=existing.id,
                    project_id=existing.project_id,
                    room_id=room_id,
                    message_id=event.message_id,
                    acknowledgement_sent=False,
                    detail="Duplicate message handled via database constraint",
                )
            raise

        logger.info(
            "Successfully created incident #%s from Switch room '%s' for project '%s'",
            incident.id,
            room_id,
            project.name,
        )

        # 5. Outgoing Switch Acknowledgement
        acknowledgement_sent = await self._send_acknowledgement(
            incident=incident,
            project_name=project.name,
            room_id=room_id,
            thread_id=event.thread_id or event.message_id,
            db=db,
        )

        return SwitchIntakeResult(
            status="created",
            incident_id=incident.id,
            project_id=project.id,
            room_id=room_id,
            message_id=event.message_id,
            acknowledgement_sent=acknowledgement_sent,
            detail="Incident successfully created and acknowledged",
        )

    async def _send_acknowledgement(
        self,
        incident,
        project_name: str,
        room_id: str,
        thread_id: Optional[str],
        db: Session,
    ) -> bool:
        """Send confirmation reply to the Switch room. Isolated from DB transaction."""
        client = self._get_client()
        ack_message = (
            f"Incident #{incident.id} opened for project '{project_name}'. "
            f"Status: {incident.status.value}. An automated triage intake has been logged."
        )

        try:
            response = await client.send_message(
                room_id=room_id,
                content=ack_message,
                thread_id=thread_id,
            )
            success = response.success
        except Exception as exc:
            logger.warning("Failed to dispatch Switch acknowledgement: %s", type(exc).__name__)
            success = False

        # Audit acknowledgement outcome
        try:
            action = "switch_acknowledgement_sent" if success else "switch_acknowledgement_failed"
            self._record_audit(
                db=db,
                actor_identifier="switch_bridge",
                action=action,
                resource_type="incident",
                resource_id=incident.id,
                details={"room_id": room_id, "thread_id": thread_id, "success": success},
            )
            db.commit()
        except Exception as exc:
            logger.debug("Failed to record acknowledgement audit log: %s", exc)

        return success

    def _record_audit(
        self,
        db: Session,
        actor_identifier: str,
        action: str,
        resource_type: str,
        details: dict,
        resource_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Helper to create an audit log entry."""
        audit_in = AuditLogCreate(
            actor_type="switch_intake",
            actor_identifier=actor_identifier,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
        AuditLogRepository.append(db, audit_in)

