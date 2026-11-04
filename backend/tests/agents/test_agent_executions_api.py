import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.agent_execution import AgentExecutionStatus, AgentType
from app.repositories import AgentExecutionRepository, IncidentRepository, ProjectRepository
from app.schemas.agent_execution import AgentExecutionCreate
from app.schemas.incident import IncidentCreate
from app.schemas.project import ProjectCreate


def test_get_agent_execution_success(client_with_db: TestClient, db_session: Session):
    project = ProjectRepository.create(
        db_session,
        ProjectCreate(name="Payment Service", environment="production"),
    )
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=project.id,
            title="Gateway 504 Gateway Timeout",
            description="Upstream gateway timed out after 30s",
        ),
    )
    db_session.commit()

    execution = AgentExecutionRepository.create(
        db_session,
        AgentExecutionCreate(
            incident_id=incident.id,
            agent_type=AgentType.INCIDENT_MANAGER,
            input_data={"incident_id": str(incident.id), "provider": "gemini", "api_key": "secret123"},
        ),
    )
    AgentExecutionRepository.update_status(
        db_session,
        execution,
        status=AgentExecutionStatus.COMPLETED,
        output_data={
            "incident_summary": "Upstream timeout identified in Payment Service.",
            "confidence_score": 0.88,
        },
    )
    db_session.commit()

    response = client_with_db.get(f"/api/v1/agent-executions/{execution.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == str(execution.id)
    assert data["data"]["status"] == "COMPLETED"
    assert data["data"]["output_data"]["confidence_score"] == 0.88

    # Verify input_data was sanitized (no raw api_key leaked)
    assert data["data"]["input_data"]["api_key"] == "*** redacted ***"


def test_get_agent_execution_not_found(client_with_db: TestClient):
    random_id = uuid.uuid4()
    response = client_with_db.get(f"/api/v1/agent-executions/{random_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert f"Agent execution with ID '{random_id}' not found" in data["message"]
