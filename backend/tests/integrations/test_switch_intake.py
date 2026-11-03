import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.incident import IncidentStatus
from app.repositories import (
    ProjectRepository,
    IncidentRepository,
    AuditLogRepository,
)
from app.schemas.project import ProjectCreate
from app.integrations.switch.client import SwitchClient
from app.integrations.switch.schemas import (
    SwitchInboundEvent,
    SwitchOperationResponse,
)
from app.integrations.switch.service import SwitchIntakeService


@pytest.fixture
def test_project(db_session: Session):
    """Seed a test project for room mapping."""
    return ProjectRepository.create(
        db_session,
        ProjectCreate(
            name="Payments API",
            description="Processes checkout transactions",
            environment="production",
        ),
    )


@pytest.fixture
def mock_switch_client():
    """Mock SwitchClient to verify outbound acknowledgement calls."""
    client = MagicMock(spec=SwitchClient)
    client.send_message = AsyncMock(
        return_value=SwitchOperationResponse(
            success=True,
            operation="send_message",
            data={"message_id": "ack-001", "status": "sent"},
        )
    )
    return client


# ---------------------------------------------------------------------------
# Test 1, 2, 3, 4: Valid Message Intake Workflow
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_valid_message_creates_incident_and_events(
    db_session: Session, test_project, mock_switch_client
) -> None:
    """1-4: Verify a valid Switch message creates an Incident, IncidentEvent, AuditLog, and maps to the correct Project."""
    with patch.object(settings, "SWITCH_ROOM_PROJECT_MAPPING", {"ops-payments": "Payments API"}):
        service = SwitchIntakeService(switch_client=mock_switch_client)

        event = SwitchInboundEvent(
            event_type="room_message",
            room_id="ops-payments",
            message_id="msg-uuid-101",
            sender_id="devops-alice",
            sender_name="Alice DevOps",
            content="High 502 error rates on /checkout endpoint",
            thread_id="root-thread-101",
        )

        result = await service.process_inbound_event(event, db=db_session)

        # 1. Incident creation verified
        assert result.status == "created"
        assert result.incident_id is not None
        assert result.acknowledgement_sent is True

        incident = IncidentRepository.get_by_id(db_session, result.incident_id)
        assert incident is not None
        assert incident.title == "Switch Incident: High 502 error rates on /checkout endpoint"
        assert incident.description == "High 502 error rates on /checkout endpoint"
        assert incident.status == IncidentStatus.OPEN
        assert incident.source == "switch"
        assert incident.source_id == "switch:ops-payments:msg-uuid-101"

        # 4. Correct project associated
        assert incident.project_id == test_project.id

        # 2. Original message preserved as IncidentEvent
        events = IncidentRepository.list_events_by_incident(db_session, incident.id)
        assert len(events) == 1
        assert events[0].event_type == "switch_message"
        assert events[0].actor_identifier == "devops-alice"
        assert events[0].description == "High 502 error rates on /checkout endpoint"
        assert events[0].event_metadata["room_id"] == "ops-payments"
        assert events[0].event_metadata["message_id"] == "msg-uuid-101"
        assert events[0].event_metadata["thread_id"] == "root-thread-101"

        # 3. AuditLog created
        logs = AuditLogRepository.get_by_resource(db_session, "incident", incident.id)
        action_names = [log.action for log in logs]
        assert "incident_created_via_switch" in action_names
        assert "switch_acknowledgement_sent" in action_names


# ---------------------------------------------------------------------------
# Test 5 & 6: Unmapped / Unauthorized Room Rejection
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_unmapped_room_is_rejected(db_session: Session, mock_switch_client) -> None:
    """5 & 6: Verify messages from unmapped or unauthorized rooms are rejected with an audit log."""
    with patch.object(settings, "SWITCH_ROOM_PROJECT_MAPPING", {"authorized-room": "Valid Project"}):
        service = SwitchIntakeService(switch_client=mock_switch_client)

        event = SwitchInboundEvent(
            event_type="room_message",
            room_id="random-general-chat",
            message_id="msg-unmapped-01",
            content="Who is on call today?",
        )

        result = await service.process_inbound_event(event, db=db_session)

        assert result.status == "rejected_unmapped_room"
        assert result.incident_id is None
        assert result.acknowledgement_sent is False

        # No incident created
        all_incidents = IncidentRepository.list(db_session)
        assert len(all_incidents) == 0

        # Auditable rejection logged
        logs = AuditLogRepository.list(db_session)
        assert len(logs) == 1
        assert logs[0].action == "switch_room_unmapped_rejected"
        assert logs[0].details["room_id"] == "random-general-chat"


# ---------------------------------------------------------------------------
# Test 7, 8, 14: Database-Backed Idempotency & Duplicate Handling
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_duplicate_message_rejected_without_new_incident(
    db_session: Session, test_project, mock_switch_client
) -> None:
    """7 & 14: Verify duplicate message does not create a second incident and does not trigger duplicate acknowledgement."""
    with patch.object(settings, "SWITCH_ROOM_PROJECT_MAPPING", {"ops-payments": "Payments API"}):
        service = SwitchIntakeService(switch_client=mock_switch_client)

        event = SwitchInboundEvent(
            event_type="room_message",
            room_id="ops-payments",
            message_id="msg-unique-555",
            content="Database connection timeout",
        )

        # First intake: creates incident
        res1 = await service.process_inbound_event(event, db=db_session)
        assert res1.status == "created"
        assert res1.acknowledgement_sent is True
        mock_switch_client.send_message.assert_called_once()

        mock_switch_client.send_message.reset_mock()

        # Second intake (identical message_id): duplicate detected
        res2 = await service.process_inbound_event(event, db=db_session)
        assert res2.status == "duplicate"
        assert res2.incident_id == res1.incident_id
        # 14. Duplicate delivery does not trigger duplicate acknowledgement
        assert res2.acknowledgement_sent is False
        mock_switch_client.send_message.assert_not_called()

        # Ensure only 1 incident exists
        all_incidents = IncidentRepository.list(db_session)
        assert len(all_incidents) == 1


@pytest.mark.anyio
async def test_concurrent_duplicate_handling_via_db_constraint(
    db_session: Session, test_project, mock_switch_client
) -> None:
    """8: Verify concurrent duplicate insertion conflict is caught by database unique constraint."""
    with patch.object(settings, "SWITCH_ROOM_PROJECT_MAPPING", {"ops-payments": "Payments API"}):
        service = SwitchIntakeService(switch_client=mock_switch_client)

        event = SwitchInboundEvent(
            event_type="room_message",
            room_id="ops-payments",
            message_id="msg-race-001",
            content="Gateway CPU spike",
        )

        # Process initial
        res1 = await service.process_inbound_event(event, db=db_session)
        assert res1.status == "created"

        # Simulate concurrent arrival bypassing the initial check (e.g. race before commit)
        existing_incident = IncidentRepository.get_by_id(db_session, res1.incident_id)
        with patch.object(IncidentRepository, "get_by_source_id", side_effect=[None, existing_incident]):
            res2 = await service.process_inbound_event(event, db=db_session)
            assert res2.status == "duplicate"
            assert res2.incident_id == res1.incident_id


# ---------------------------------------------------------------------------
# Test 9 & 10: Outbound Acknowledgement & Delivery Failure Isolation
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_acknowledgement_contains_correct_incident_id(
    db_session: Session, test_project, mock_switch_client
) -> None:
    """9: Verify outbound acknowledgement contains the exact created incident ID and project name."""
    with patch.object(settings, "SWITCH_ROOM_PROJECT_MAPPING", {"ops-payments": "Payments API"}):
        service = SwitchIntakeService(switch_client=mock_switch_client)

        event = SwitchInboundEvent(
            event_type="room_message",
            room_id="ops-payments",
            message_id="msg-ack-check",
            content="Disk full on worker-01",
            thread_id="thread-888",
        )

        result = await service.process_inbound_event(event, db=db_session)
        assert result.status == "created"

        mock_switch_client.send_message.assert_called_once()
        call_kwargs = mock_switch_client.send_message.call_args.kwargs
        assert call_kwargs["room_id"] == "ops-payments"
        assert f"Incident #{result.incident_id}" in call_kwargs["content"]
        assert "Payments API" in call_kwargs["content"]
        assert call_kwargs["thread_id"] == "thread-888"


@pytest.mark.anyio
async def test_acknowledgement_failure_does_not_rollback_incident(
    db_session: Session, test_project
) -> None:
    """10: Verify outbound network failure does not delete or roll back the committed incident."""
    failing_client = MagicMock(spec=SwitchClient)
    failing_client.send_message = AsyncMock(side_effect=RuntimeError("Switch API network timeout"))

    with patch.object(settings, "SWITCH_ROOM_PROJECT_MAPPING", {"ops-payments": "Payments API"}):
        service = SwitchIntakeService(switch_client=failing_client)

        event = SwitchInboundEvent(
            event_type="room_message",
            room_id="ops-payments",
            message_id="msg-network-fail",
            content="Pod CrashLoopBackOff",
        )

        result = await service.process_inbound_event(event, db=db_session)

        # Incident is preserved despite ack failure
        assert result.status == "created"
        assert result.acknowledgement_sent is False
        assert result.incident_id is not None

        incident = IncidentRepository.get_by_id(db_session, result.incident_id)
        assert incident is not None
        assert incident.title == "Switch Incident: Pod CrashLoopBackOff"

        # Acknowledgement failure audited
        logs = AuditLogRepository.get_by_resource(db_session, "incident", incident.id)
        action_names = [log.action for log in logs]
        assert "switch_acknowledgement_failed" in action_names


# ---------------------------------------------------------------------------
# Test 11: Database Failure Handling
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_database_failure_returns_explicit_error_without_false_success(
    mock_switch_client,
) -> None:
    """11: Verify database connection failure returns explicit persistence failure and no false success."""
    with patch.object(settings, "SWITCH_ROOM_PROJECT_MAPPING", {"ops-payments": "Payments API"}):
        service = SwitchIntakeService(switch_client=mock_switch_client)

        event = SwitchInboundEvent(
            event_type="room_message",
            room_id="ops-payments",
            message_id="msg-db-fail",
            content="Service down",
        )

        # Force database failure via bad session
        broken_session = MagicMock(spec=Session)
        broken_session.scalar.side_effect = RuntimeError("Database unreachable")

        result = await service.process_inbound_event(event, db=broken_session)
        assert result.status == "persistence_failure"
        assert result.incident_id is None
        assert result.acknowledgement_sent is False
        assert "Persistence failed" in result.detail


# ---------------------------------------------------------------------------
# Test 12 & 13: Malformed & Oversized Messages
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_malformed_event_missing_identifiers_rejected(
    db_session: Session, mock_switch_client
) -> None:
    """12: Verify message missing room_id or message_id or with whitespace-only content is rejected."""
    service = SwitchIntakeService(switch_client=mock_switch_client)

    # Missing message_id
    event1 = SwitchInboundEvent(
        event_type="room_message",
        room_id="ops-room",
        message_id=None,
        content="Test alert",
    )
    res1 = await service.process_inbound_event(event1, db=db_session)
    assert res1.status == "invalid_event"

    # Whitespace-only content
    event2 = SwitchInboundEvent(
        event_type="room_message",
        room_id="ops-room",
        message_id="msg-whitespace",
        content="     ",
    )
    res2 = await service.process_inbound_event(event2, db=db_session)
    assert res2.status == "invalid_event"


def test_oversized_message_rejected_by_schema_boundary() -> None:
    """13: Verify message exceeding maximum length boundary is rejected by schema validator."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SwitchInboundEvent(
            event_type="room_message",
            room_id="ops-room",
            message_id="msg-oversized",
            content="A" * 15000,
        )


@pytest.mark.anyio
async def test_cross_room_identical_message_ids_do_not_collide(
    db_session: Session, test_project, mock_switch_client
) -> None:
    """14: Verify identical message_id across two distinct rooms generates separate incidents without collision."""
    # Create second project
    project2 = ProjectRepository.create(
        db_session,
        ProjectCreate(
            name="Auth Service",
            description="Authentication microservice",
            environment="production",
        ),
    )

    mapping = {
        "room-payments": "Payments API",
        "room-auth": "Auth Service",
    }

    with patch.object(settings, "SWITCH_ROOM_PROJECT_MAPPING", mapping):
        service = SwitchIntakeService(switch_client=mock_switch_client)

        shared_message_id = "msg-common-12345"

        event1 = SwitchInboundEvent(
            event_type="room_message",
            room_id="room-payments",
            message_id=shared_message_id,
            content="Payments checkout latency spiking",
        )
        res1 = await service.process_inbound_event(event1, db=db_session)
        assert res1.status == "created"
        assert res1.incident_id is not None

        event2 = SwitchInboundEvent(
            event_type="room_message",
            room_id="room-auth",
            message_id=shared_message_id,
            content="OAuth token generation failing",
        )
        res2 = await service.process_inbound_event(event2, db=db_session)
        assert res2.status == "created"
        assert res2.incident_id is not None
        assert res2.incident_id != res1.incident_id

        inc1 = IncidentRepository.get_by_id(db_session, res1.incident_id)
        inc2 = IncidentRepository.get_by_id(db_session, res2.incident_id)

        assert inc1.source_id == "switch:room-payments:msg-common-12345"
        assert inc2.source_id == "switch:room-auth:msg-common-12345"
        assert inc1.project_id == test_project.id
        assert inc2.project_id == project2.id

