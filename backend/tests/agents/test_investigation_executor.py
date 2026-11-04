import uuid
import pytest
from unittest.mock import MagicMock
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.orm import Session

from app.agents.llm.exceptions import LLMConfigurationError
from app.agents.runtime.executor import IncidentInvestigationExecutor
from app.agents.schemas.investigation import InvestigationResult
from app.models.agent_execution import AgentExecutionStatus
from app.models.incident import IncidentSeverity, IncidentStatus
from app.repositories import (
    AgentExecutionRepository,
    AuditLogRepository,
    IncidentRepository,
    ProjectRepository,
)
from app.schemas.incident import IncidentCreate, IncidentEventCreate
from app.schemas.project import ProjectCreate


@pytest.fixture
def test_project(db_session: Session):
    return ProjectRepository.create(
        db_session,
        ProjectCreate(
            name="Auth Service",
            description="User authentication service",
            environment="production",
        ),
    )


@pytest.fixture
def test_incident(db_session: Session, test_project):
    inc = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=test_project.id,
            title="High Latency on Token Verification",
            description="JWT verification latency spiked above 1200ms",
            severity=IncidentSeverity.CRITICAL,
            status=IncidentStatus.OPEN,
            source="switch",
            source_id="switch:room-auth:msg-445",
        ),
    )
    IncidentRepository.create_event(
        db_session,
        IncidentEventCreate(
            incident_id=inc.id,
            event_type="switch_message",
            actor_type="switch_user",
            actor_identifier="devops-alice",
            description="Investigating JWT timeouts across ingress",
            event_metadata={"room_id": "room-auth"},
        ),
    )
    db_session.commit()
    return inc


def test_executor_persists_agent_execution_and_audit_log(
    db_session: Session, test_incident
) -> None:
    """Verify executor creates AgentExecution, invokes graph, and logs audit record."""
    mock_result = InvestigationResult(
        incident_summary="JWT verification bottleneck under sudden auth traffic spike.",
        observed_facts=["Latency spiked to 1200ms on token verification."],
        hypotheses=["Redis token revocation cache miss storm."],
        supporting_evidence=["JWT verification queries falling back to primary database."],
        confidence_score=0.91,
        recommended_diagnostic_steps=["Check Redis cache hit ratio on auth keys."],
        recommended_next_actions=["Scale Redis read replicas."],
        missing_information=["Redis memory fragmentation telemetry."],
    )

    mock_llm = MagicMock(spec=BaseChatModel)
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_result
    mock_llm.with_structured_output.return_value = mock_structured

    response = IncidentInvestigationExecutor.execute(
        db=db_session,
        incident_id=test_incident.id,
        llm=mock_llm,
    )

    assert response.incident_id == test_incident.id
    assert response.execution_status == "COMPLETED"
    assert response.investigation.confidence_score == 0.91

    # Verify AgentExecution record
    exec_record = AgentExecutionRepository.get_by_id(db_session, response.execution_id)
    assert exec_record is not None
    assert exec_record.status == AgentExecutionStatus.COMPLETED
    assert exec_record.completed_at is not None
    assert "JWT verification bottleneck" in exec_record.output_data["incident_summary"]

    # Verify incident root cause summary updated
    db_session.refresh(test_incident)
    assert test_incident.root_cause_summary == "Redis token revocation cache miss storm."

    # Verify AuditLog created
    audit_logs = AuditLogRepository.get_by_resource(db_session, "incident", test_incident.id)
    actions = [log.action for log in audit_logs]
    assert "agent_investigation_completed" in actions


def test_executor_raises_for_nonexistent_incident(db_session: Session) -> None:
    """Verify executor raises ValueError when incident does not exist."""
    random_id = uuid.uuid4()
    with pytest.raises(ValueError) as exc_info:
        IncidentInvestigationExecutor.execute(
            db=db_session,
            incident_id=random_id,
        )
    assert "not found" in str(exc_info.value)


def test_executor_handles_llm_configuration_error(
    db_session: Session, test_incident
) -> None:
    """Verify executor marks AgentExecution as FAILED when LLM credentials are unconfigured."""
    with pytest.raises(LLMConfigurationError):
        IncidentInvestigationExecutor.execute(
            db=db_session,
            incident_id=test_incident.id,
            provider="unsupported-provider-test",
        )

    # Check that failed execution was persisted
    executions = AgentExecutionRepository.list_by_incident(db_session, test_incident.id)
    assert len(executions) > 0
    failed_exec = executions[0]
    assert failed_exec.status == AgentExecutionStatus.FAILED
    assert "LLMConfigurationError" in (failed_exec.error_summary or "")

