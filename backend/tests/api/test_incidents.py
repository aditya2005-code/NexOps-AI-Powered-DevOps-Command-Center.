import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.incident import IncidentSeverity, IncidentStatus
from app.repositories import IncidentRepository, ProjectRepository
from app.schemas.incident import IncidentCreate, IncidentEventCreate
from app.schemas.project import ProjectCreate


@pytest.fixture
def sample_project(db_session: Session):
    return ProjectRepository.create(
        db_session,
        ProjectCreate(
            name="Checkout Gateway",
            description="Payment gateway service",
            environment="production",
        ),
    )


@pytest.fixture
def sample_incidents(db_session: Session, sample_project):
    inc1 = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=sample_project.id,
            title="High Latency on Checkout",
            description="Latency exceeded 500ms on /pay endpoint",
            severity=IncidentSeverity.CRITICAL,
            status=IncidentStatus.OPEN,
            source="switch",
            source_id="switch:room-ops:msg-001",
        ),
    )
    inc2 = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=sample_project.id,
            title="Memory leak in worker",
            description="Worker memory consumption steady growth",
            severity=IncidentSeverity.MEDIUM,
            status=IncidentStatus.RESOLVED,
            source="telemetry",
            source_id="telemetry:host-worker-2",
        ),
    )
    IncidentRepository.create_event(
        db_session,
        IncidentEventCreate(
            incident_id=inc1.id,
            event_type="switch_message",
            actor_type="switch_user",
            actor_identifier="devops-dan",
            description="Investigating latency spikes",
            event_metadata={"room_id": "room-ops"},
        ),
    )
    db_session.commit()
    return [inc1, inc2]


def test_list_incidents_empty(client_with_db: TestClient) -> None:
    """Verify listing incidents returns an empty list when no incidents exist."""
    response = client_with_db.get("/api/v1/incidents")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Incidents retrieved successfully"
    assert data["data"] == []


def test_list_incidents_populated(client_with_db: TestClient, sample_incidents) -> None:
    """Verify listing incidents returns persisted incidents with project names."""
    response = client_with_db.get("/api/v1/incidents")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 2
    titles = [inc["title"] for inc in data["data"]]
    assert "High Latency on Checkout" in titles
    assert "Memory leak in worker" in titles

    # Verify project_name is populated
    for inc in data["data"]:
        assert inc["project_name"] == "Checkout Gateway"


def test_list_incidents_filtering(client_with_db: TestClient, sample_incidents) -> None:
    """Verify filtering by status and severity."""
    # Filter by status OPEN
    resp_open = client_with_db.get("/api/v1/incidents?status=OPEN")
    assert resp_open.status_code == 200
    data_open = resp_open.json()["data"]
    assert len(data_open) == 1
    assert data_open[0]["status"] == "OPEN"

    # Filter by severity CRITICAL
    resp_crit = client_with_db.get("/api/v1/incidents?severity=CRITICAL")
    assert resp_crit.status_code == 200
    data_crit = resp_crit.json()["data"]
    assert len(data_crit) == 1
    assert data_crit[0]["severity"] == "CRITICAL"


def test_list_incidents_pagination(client_with_db: TestClient, sample_incidents) -> None:
    """Verify skip and limit parameters."""
    response = client_with_db.get("/api/v1/incidents?skip=0&limit=1")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1


def test_list_incidents_invalid_pagination(client_with_db: TestClient) -> None:
    """Verify validation error on invalid limit."""
    response = client_with_db.get("/api/v1/incidents?limit=0")
    assert response.status_code in (400, 422)


def test_get_incident_detail_success(client_with_db: TestClient, sample_incidents) -> None:
    """Verify getting incident detail by ID."""
    inc = sample_incidents[0]
    response = client_with_db.get(f"/api/v1/incidents/{inc.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(inc.id)
    assert data["title"] == "High Latency on Checkout"
    assert data["source"] == "switch"
    assert data["source_id"] == "switch:room-ops:msg-001"
    assert data["project_name"] == "Checkout Gateway"


def test_get_incident_detail_not_found(client_with_db: TestClient) -> None:
    """Verify 404 response for non-existent incident ID."""
    random_id = uuid.uuid4()
    response = client_with_db.get(f"/api/v1/incidents/{random_id}")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert f"Incident with ID '{random_id}' not found" in body["message"]


def test_get_incident_events(client_with_db: TestClient, sample_incidents) -> None:
    """Verify retrieving event log for an incident."""
    inc = sample_incidents[0]
    response = client_with_db.get(f"/api/v1/incidents/{inc.id}/events")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["event_type"] == "switch_message"
    assert data[0]["actor_identifier"] == "devops-dan"
    assert data[0]["description"] == "Investigating latency spikes"


def test_incident_stats_summary(client_with_db: TestClient, sample_incidents) -> None:
    """Verify aggregate summary metrics."""
    response = client_with_db.get("/api/v1/incidents/stats/summary")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert data["open"] == 1
    assert data["resolved"] == 1
    assert data["investigating"] == 0
