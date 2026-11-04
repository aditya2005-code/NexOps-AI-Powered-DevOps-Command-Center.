from unittest.mock import MagicMock
from langchain_core.language_models.chat_models import BaseChatModel

from app.agents.schemas.investigation import InvestigationResult
from app.agents.state import InvestigationState
from app.agents.workflows.incident_investigation import create_investigation_graph


def test_successful_investigation_workflow() -> None:
    """Verify end-to-end execution of investigation graph with structured output."""
    mock_result = InvestigationResult(
        incident_summary="Database connection pool exhaustion on Payments API.",
        observed_facts=["PostgreSQL pool timeout errors reported in logs.", "Latency exceeded 10s."],
        hypotheses=["Connection leak in order checkout handler."],
        supporting_evidence=["Active pool connections remained at max (20/20) indefinitely."],
        confidence_score=0.88,
        recommended_diagnostic_steps=["Query pg_stat_activity for idle-in-transaction sessions."],
        recommended_next_actions=["Restart worker pods to release leaked connections."],
        missing_information=["Thread dump during latency peak."],
    )

    mock_llm = MagicMock(spec=BaseChatModel)
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_result
    mock_llm.with_structured_output.return_value = mock_structured

    graph = create_investigation_graph(llm=mock_llm)

    initial_state: InvestigationState = {
        "incident_id": "inc-test-101",
        "incident_title": "Database connection pool timeout",
        "incident_description": "Multiple 500 errors on /checkout due to pool timeout",
        "incident_severity": "CRITICAL",
        "incident_status": "OPEN",
        "incident_source": "switch",
        "project_name": "Payments Service",
        "project_environment": "production",
        "incident_events": [
            {
                "event_type": "switch_message",
                "actor_identifier": "alice",
                "description": "Payments checkout is timing out",
                "created_at": "2026-11-04T10:00:00Z",
            }
        ],
        "errors": [],
    }

    final_state = graph.invoke(initial_state)

    assert final_state["execution_status"] == "completed"
    assert len(final_state["errors"]) == 0
    assert final_state["investigation_result"] is not None
    assert final_state["investigation_result"]["confidence_score"] == 0.88
    assert "Database connection pool exhaustion" in final_state["investigation_result"]["incident_summary"]


def test_workflow_handles_missing_incident_context() -> None:
    """Verify workflow executes cleanly even when incident description and events are empty."""
    mock_result = InvestigationResult(
        incident_summary="Incident with minimal context reported.",
        observed_facts=["Incident title: Unknown Error"],
        hypotheses=["Insufficient context to deduce definitive root cause."],
        supporting_evidence=[],
        confidence_score=0.2,
        recommended_diagnostic_steps=["Inspect system logs and traces for affected services."],
        recommended_next_actions=["Contact incident reporter for reproduction steps."],
        missing_information=["No description or timeline events provided."],
    )

    mock_llm = MagicMock(spec=BaseChatModel)
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_result
    mock_llm.with_structured_output.return_value = mock_structured

    graph = create_investigation_graph(llm=mock_llm)

    minimal_state: InvestigationState = {
        "incident_id": "inc-empty-001",
        "incident_title": "Unknown Error",
        "incident_description": None,
        "incident_severity": "LOW",
        "incident_status": "OPEN",
        "incident_source": "telemetry",
        "project_name": None,
        "project_environment": None,
        "incident_events": [],
        "errors": [],
    }

    final_state = graph.invoke(minimal_state)
    assert final_state["execution_status"] == "completed"
    assert final_state["investigation_result"]["confidence_score"] == 0.2


def test_workflow_model_failure_gracefully_handled() -> None:
    """Verify workflow captures model invocation failure and produces safe fallback result."""
    mock_llm = MagicMock(spec=BaseChatModel)
    mock_structured = MagicMock()
    mock_structured.invoke.side_effect = RuntimeError("Provider 503 Overloaded")
    mock_llm.with_structured_output.return_value = mock_structured

    graph = create_investigation_graph(llm=mock_llm)

    state: InvestigationState = {
        "incident_id": "inc-err-999",
        "incident_title": "High CPU load",
        "incident_severity": "HIGH",
        "incident_status": "OPEN",
        "incident_source": "telemetry",
        "incident_events": [],
        "errors": [],
    }

    final_state = graph.invoke(state)

    assert final_state["execution_status"] == "failed"
    assert len(final_state["errors"]) > 0
    assert "Provider 503 Overloaded" in final_state["errors"][0]

    # Verify safe fallback output is generated
    res = final_state["investigation_result"]
    assert res is not None
    assert res["confidence_score"] == 0.0
    assert "Automated investigation failed" in res["incident_summary"]

