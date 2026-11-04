import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agents.runtime.executor import IncidentInvestigationExecutor
from app.agents.schemas.investigation import (
    IncidentInvestigationResponse,
    InvestigationResult,
)
from app.models.incident import IncidentSeverity, IncidentStatus
from app.repositories import IncidentRepository, ProjectRepository
from app.schemas.incident import IncidentCreate
from app.schemas.project import ProjectCreate


def test_investigate_endpoint_success(client_with_db: TestClient, db_session: Session) -> None:
    """Verify POST /api/v1/incidents/{id}/investigate returns structured result."""
    project = ProjectRepository.create(
        db_session,
        ProjectCreate(name="Ingress Gateway", environment="production"),
    )
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=project.id,
            title="Gateway 502 Bad Gateway Spike",
            description="High error rate on /api route",
            severity=IncidentSeverity.HIGH,
            status=IncidentStatus.OPEN,
        ),
    )
    db_session.commit()

    mock_investigation = InvestigationResult(
        incident_summary="Upstream connection drop in Ingress Gateway.",
        observed_facts=["502 Bad Gateway responses on /api"],
        hypotheses=["Upstream backend pod killed by OOMKiller."],
        supporting_evidence=["Sudden drop in healthy upstream endpoints."],
        confidence_score=0.85,
        recommended_diagnostic_steps=["kubectl describe pod on upstream deployments."],
        recommended_next_actions=["Increase memory limits for upstream service."],
        missing_information=["Kernel OOM logs."],
    )

    mock_resp = IncidentInvestigationResponse(
        incident_id=incident.id,
        execution_id=uuid.uuid4(),
        provider="gemini",
        model="gemini-1.5-flash",
        investigation=mock_investigation,
        execution_status="COMPLETED",
        duration_seconds=0.45,
        created_at=incident.created_at,
    )

    with patch.object(IncidentInvestigationExecutor, "execute", return_value=mock_resp):
        response = client_with_db.post(f"/api/v1/incidents/{incident.id}/investigate")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Incident investigation completed successfully"
        assert data["data"]["incident_id"] == str(incident.id)
        assert data["data"]["investigation"]["confidence_score"] == 0.85
        assert "X-Request-ID" in response.headers


def test_investigate_endpoint_not_found(client_with_db: TestClient) -> None:
    """Verify POST /api/v1/incidents/{id}/investigate returns 404 for unknown incident."""
    random_id = uuid.uuid4()
    response = client_with_db.post(f"/api/v1/incidents/{random_id}/investigate")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert f"Incident with ID '{random_id}' not found" in data["message"]


def test_investigate_endpoint_provider_unconfigured_503(
    client_with_db: TestClient, db_session: Session
) -> None:
    """Verify 503 response when LLM provider credentials are not configured."""
    project = ProjectRepository.create(
        db_session,
        ProjectCreate(name="Billing API", environment="production"),
    )
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=project.id,
            title="Billing Webhook Timeout",
            severity=IncidentSeverity.MEDIUM,
            status=IncidentStatus.OPEN,
        ),
    )
    db_session.commit()

    # Request investigation with unknown/unsupported provider to trigger LLMConfigurationError
    response = client_with_db.post(
        f"/api/v1/incidents/{incident.id}/investigate?provider=unknown-ai-provider"
    )
    assert response.status_code == 503
    data = response.json()
    assert data["success"] is False
    assert "Unsupported LLM provider" in data["message"]

