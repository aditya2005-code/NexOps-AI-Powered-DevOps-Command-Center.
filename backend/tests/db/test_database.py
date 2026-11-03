import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models import (
    Project,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    IncidentEvent,
    AgentExecution,
    AgentType,
    AgentExecutionStatus,
    CodePatch,
    Approval,
    ApprovalDecision,
    TestExecution,
    TestExecutionStatus,
    AuditLog,
)
from app.repositories import (
    ProjectRepository,
    IncidentRepository,
    AgentExecutionRepository,
    CodePatchRepository,
    ApprovalRepository,
    AuditLogRepository,
)
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.incident import IncidentCreate, IncidentEventCreate
from app.schemas.agent_execution import AgentExecutionCreate
from app.schemas.code_patch import CodePatchCreate
from app.schemas.approval import ApprovalCreate
from app.schemas.audit_log import AuditLogCreate
from app.db.dependencies import get_db
from app.main import app as fastapi_app


# ---------------------------------------------------------------------------
# 1. Model Construction
# ---------------------------------------------------------------------------
def test_model_construction(db_session: Session) -> None:
    """Verify that core entities can be instantiated and mapped properly."""
    project = Project(
        name="Test Gateway",
        description="API Gateway Service",
        repository_url="https://github.com/nexops/gateway",
        default_branch="main",
        environment="staging",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    assert isinstance(project.id, uuid.UUID)
    assert project.name == "Test Gateway"
    assert project.created_at is not None
    assert project.updated_at is not None


# ---------------------------------------------------------------------------
# 2. Project Creation & Repository CRUD
# ---------------------------------------------------------------------------
def test_project_repository_crud(db_session: Session) -> None:
    """Verify Project CRUD operations and constraints via ProjectRepository."""
    data = ProjectCreate(
        name="Billing Service",
        description="Processes payments",
        repository_url="https://github.com/nexops/billing",
        environment="production",
    )
    project = ProjectRepository.create(db_session, data)
    assert project.id is not None
    assert project.name == "Billing Service"
    assert project.default_branch == "main"
    assert project.status == "active"

    # Get by ID and Name
    fetched = ProjectRepository.get_by_id(db_session, project.id)
    assert fetched is not None and fetched.id == project.id
    by_name = ProjectRepository.get_by_name(db_session, "Billing Service")
    assert by_name is not None and by_name.id == project.id

    # Update
    updated = ProjectRepository.update(db_session, project, ProjectUpdate(description="Updated description"))
    assert updated.description == "Updated description"

    # List
    all_projects = ProjectRepository.list(db_session)
    assert len(all_projects) >= 1

    # Delete
    ProjectRepository.delete(db_session, project)
    assert ProjectRepository.get_by_id(db_session, project.id) is None


# ---------------------------------------------------------------------------
# 3. Incident Creation & Repository
# ---------------------------------------------------------------------------
def test_incident_repository_operations(db_session: Session) -> None:
    """Verify Incident creation and status progression via IncidentRepository."""
    project = ProjectRepository.create(db_session, ProjectCreate(name="Core API"))
    inc_data = IncidentCreate(
        project_id=project.id,
        title="High Memory Usage in Pod",
        description="Memory exceeded 90% threshold",
        severity=IncidentSeverity.HIGH,
    )
    incident = IncidentRepository.create(db_session, inc_data)

    assert incident.id is not None
    assert incident.project_id == project.id
    assert incident.status == IncidentStatus.OPEN
    assert incident.severity == IncidentSeverity.HIGH

    # Status update
    updated_incident = IncidentRepository.update_status(
        db_session, incident, IncidentStatus.INVESTIGATING
    )
    assert updated_incident.status == IncidentStatus.INVESTIGATING


# ---------------------------------------------------------------------------
# 4. Foreign Key Relationships
# ---------------------------------------------------------------------------
def test_foreign_key_relationships(db_session: Session) -> None:
    """Verify foreign key constraint enforcement and relationship mapping."""
    project = ProjectRepository.create(db_session, ProjectCreate(name="Auth Service"))

    incident = Incident(
        project_id=project.id,
        title="Token Verification Latency",
        severity=IncidentSeverity.MEDIUM,
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(project)

    assert len(project.incidents) == 1
    assert project.incidents[0].title == "Token Verification Latency"
    assert incident.project.name == "Auth Service"

    # Foreign key violation test (nonexistent project_id)
    with pytest.raises(IntegrityError):
        invalid_incident = Incident(
            project_id=uuid.uuid4(),
            title="Orphan Incident",
            severity=IncidentSeverity.LOW,
        )
        db_session.add(invalid_incident)
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# 5. Incident Event Creation & JSON Metadata
# ---------------------------------------------------------------------------
def test_incident_event_creation(db_session: Session) -> None:
    """Verify incident event timeline and JSON metadata serialization."""
    project = ProjectRepository.create(db_session, ProjectCreate(name="Search Worker"))
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(project_id=project.id, title="Elasticsearch cluster disconnect"),
    )

    event_in = IncidentEventCreate(
        incident_id=incident.id,
        event_type="alert_received",
        actor_type="system",
        actor_identifier="prometheus-alertmanager",
        description="Alert fired: ES Cluster Red",
        event_metadata={"node_count": 3, "unassigned_shards": 12},
    )
    event = IncidentRepository.create_event(db_session, event_in)

    assert event.id is not None
    assert event.incident_id == incident.id
    assert event.event_metadata["node_count"] == 3
    assert event.event_metadata["unassigned_shards"] == 12

    events = IncidentRepository.list_events_by_incident(db_session, incident.id)
    assert len(events) == 1
    assert events[0].event_type == "alert_received"


# ---------------------------------------------------------------------------
# 6. Agent Execution Persistence
# ---------------------------------------------------------------------------
def test_agent_execution_lifecycle(db_session: Session) -> None:
    """Verify agent execution tracking with structured input and output payloads."""
    project = ProjectRepository.create(db_session, ProjectCreate(name="Metrics Collector"))
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(project_id=project.id, title="High CPU consumption"),
    )

    execution = AgentExecutionRepository.create(
        db_session,
        AgentExecutionCreate(
            incident_id=incident.id,
            agent_type=AgentType.INCIDENT_MANAGER,
            input_data={"metrics": {"cpu_utilization": 98.4}, "pod": "metrics-7fbd-1"},
        ),
    )

    assert execution.id is not None
    assert execution.status == AgentExecutionStatus.PENDING
    assert execution.input_data["metrics"]["cpu_utilization"] == 98.4

    # Update execution to completed
    execution.status = AgentExecutionStatus.COMPLETED
    execution.output_data = {"recommendation": "Scale replica count to 3", "confidence": 0.95}
    db_session.flush()

    refreshed = AgentExecutionRepository.get_by_id(db_session, execution.id)
    assert refreshed is not None
    assert refreshed.status == AgentExecutionStatus.COMPLETED
    assert refreshed.output_data["confidence"] == 0.95


# ---------------------------------------------------------------------------
# 7. Code Patch SHA-256 Hash Verification
# ---------------------------------------------------------------------------
def test_code_patch_hash_verification(db_session: Session) -> None:
    """Verify cryptographic SHA-256 hashing and patch integrity verification."""
    project = ProjectRepository.create(db_session, ProjectCreate(name="Checkout Service"))
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(project_id=project.id, title="Null pointer on empty cart checkout"),
    )

    raw_diff = "--- a/checkout.py\n+++ b/checkout.py\n@@ -10,3 +10,4 @@\n+if not cart:\n+    return None"
    patch = CodePatchRepository.create(
        db_session,
        CodePatchCreate(
            incident_id=incident.id,
            title="Fix null pointer exception",
            description="Adds guard against empty cart dictionary",
            patch_content=raw_diff,
        ),
    )

    assert patch.id is not None
    assert len(patch.patch_hash) == 64  # Valid SHA-256 hex digest
    assert patch.patch_hash == CodePatch.compute_sha256(raw_diff)

    # Verification passes with original content
    assert CodePatchRepository.verify_patch_hash(patch, raw_diff) is True

    # Verification fails if content is tampered with
    tampered_diff = raw_diff + "\n# Malicious alteration"
    assert CodePatchRepository.verify_patch_hash(patch, tampered_diff) is False


# ---------------------------------------------------------------------------
# 8. Approval Hash Validation
# ---------------------------------------------------------------------------
def test_approval_hash_validation(db_session: Session) -> None:
    """Verify approval audit records and cryptographic matching against target patch."""
    project = ProjectRepository.create(db_session, ProjectCreate(name="User Service"))
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(project_id=project.id, title="Session timeout regression"),
    )
    diff = "--- a/session.py\n+++ b/session.py\n@@ -5,1 +5,1 @@\n-TIMEOUT = 60\n+TIMEOUT = 3600\n"
    patch = CodePatchRepository.create(
        db_session,
        CodePatchCreate(
            incident_id=incident.id,
            title="Adjust session timeout",
            patch_content=diff,
        ),
    )

    approval = ApprovalRepository.create(
        db_session,
        ApprovalCreate(
            patch_id=patch.id,
            patch_hash=patch.patch_hash,
            decision=ApprovalDecision.APPROVED,
            reviewer_identifier="alice.devops@nexops.io",
            comment="Verified timeout fix on staging",
        ),
    )

    assert approval.id is not None
    assert approval.decision == ApprovalDecision.APPROVED
    assert ApprovalRepository.validate_approval_hash(approval, patch) is True

    # Validation fails if approval points to a different/altered hash
    tampered_approval = Approval(
        patch_id=patch.id,
        patch_hash="0" * 64,
        decision=ApprovalDecision.APPROVED,
        reviewer_identifier="bad_actor",
    )
    assert ApprovalRepository.validate_approval_hash(tampered_approval, patch) is False


# ---------------------------------------------------------------------------
# 9. Audit Log Append-Only Behavior
# ---------------------------------------------------------------------------
def test_audit_log_append_behavior(db_session: Session) -> None:
    """Verify audit log append-only semantics and querying."""
    resource_uuid = uuid.uuid4()

    entry1 = AuditLogRepository.append(
        db_session,
        AuditLogCreate(
            actor_type="user",
            actor_identifier="admin@nexops.io",
            action="project_created",
            resource_type="project",
            resource_id=resource_uuid,
            details={"ip": "10.0.0.1", "role": "admin"},
        ),
    )
    entry2 = AuditLogRepository.append(
        db_session,
        AuditLogCreate(
            actor_type="agent",
            actor_identifier="triage_agent",
            action="incident_triaged",
            resource_type="incident",
            resource_id=uuid.uuid4(),
            details={"priority": "P1"},
        ),
    )

    assert entry1.id is not None
    assert entry2.id is not None

    logs = AuditLogRepository.list(db_session)
    assert len(logs) >= 2

    # Filter by resource
    res_logs = AuditLogRepository.get_by_resource(db_session, "project", resource_uuid)
    assert len(res_logs) == 1
    assert res_logs[0].action == "project_created"
    assert res_logs[0].details["ip"] == "10.0.0.1"


# ---------------------------------------------------------------------------
# 10. Repository Query Operations
# ---------------------------------------------------------------------------
def test_repository_query_filtering(db_session: Session) -> None:
    """Verify filtering and pagination across repository queries."""
    p1 = ProjectRepository.create(db_session, ProjectCreate(name="Alpha Service"))
    p2 = ProjectRepository.create(db_session, ProjectCreate(name="Beta Service"))

    IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=p1.id,
            title="Alpha Warning",
            severity=IncidentSeverity.LOW,
        ),
    )
    IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=p1.id,
            title="Alpha Outage",
            severity=IncidentSeverity.CRITICAL,
        ),
    )
    IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=p2.id,
            title="Beta Latency",
            severity=IncidentSeverity.HIGH,
        ),
    )

    # Filter by project
    p1_incidents = IncidentRepository.list_by_project(db_session, p1.id)
    assert len(p1_incidents) == 2

    p2_incidents = IncidentRepository.list_by_project(db_session, p2.id)
    assert len(p2_incidents) == 1

    # Filter by severity
    critical_incidents = IncidentRepository.list_by_severity(db_session, IncidentSeverity.CRITICAL)
    assert len(critical_incidents) == 1
    assert critical_incidents[0].title == "Alpha Outage"


# ---------------------------------------------------------------------------
# 11. Database Session Lifecycle & Rollback
# ---------------------------------------------------------------------------
def test_database_session_rollback(db_session: Session) -> None:
    """Verify that failed transactions roll back cleanly without polluting state."""
    ProjectRepository.create(db_session, ProjectCreate(name="Isolated Service"))
    db_session.commit()

    # Attempt inserting duplicate unique name
    try:
        duplicate = Project(name="Isolated Service")
        db_session.add(duplicate)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()

    # Session is operational and no duplicate was persisted
    projects = ProjectRepository.list(db_session)
    matching = [p for p in projects if p.name == "Isolated Service"]
    assert len(matching) == 1


# ---------------------------------------------------------------------------
# 12. Invalid Enum Handling
# ---------------------------------------------------------------------------
def test_invalid_enum_handling() -> None:
    """Verify that invalid enum strings fail validation."""
    with pytest.raises(ValueError):
        IncidentSeverity("EXTREME_DISASTER")

    with pytest.raises(ValueError):
        IncidentStatus("RESOLVED_FOREVER")

    with pytest.raises(ValueError):
        AgentType("HACKER_AGENT")

    with pytest.raises(ValueError):
        ApprovalDecision("MAYBE")


# ---------------------------------------------------------------------------
# 13. Database Health Endpoint
# ---------------------------------------------------------------------------
def test_database_health_endpoint_healthy(client_with_db: TestClient) -> None:
    """Verify GET /api/v1/health/database returns 200 with dialect name when healthy."""
    response = client_with_db.get("/api/v1/health/database")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert data["data"]["database"] == "sqlite"


def test_database_health_endpoint_unhealthy() -> None:
    """Verify GET /api/v1/health/database returns 503 and hides credentials on DB failure."""
    class FailingSession:
        def execute(self, *args, **kwargs):
            raise RuntimeError("Database connection timeout")

    def broken_get_db():
        yield FailingSession()

    fastapi_app.dependency_overrides[get_db] = broken_get_db
    with TestClient(fastapi_app) as client:
        response = client.get("/api/v1/health/database")
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "DATABASE_UNAVAILABLE"
        # Ensure no raw credentials or tracebacks leaked
        assert "password" not in str(data).lower()
        assert "secret" not in str(data).lower()
    fastapi_app.dependency_overrides.clear()
