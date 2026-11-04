from unittest.mock import MagicMock
from langchain_core.language_models.chat_models import BaseChatModel

from app.agents.schemas.remediation import PatchRiskLevel, ProposedPatch
from app.agents.state.remediation_state import RemediationState
from app.agents.workflows.remediation import create_remediation_graph


def test_remediation_workflow_success(tmp_path):
    ws = tmp_path / "mock_app"
    ws.mkdir()
    src = ws / "api"
    src.mkdir()
    (src / "service.py").write_text("def run():\n    return 1\n", encoding="utf-8")

    valid_diff = """--- a/api/service.py
+++ b/api/service.py
@@ -1,2 +1,3 @@
 def run():
+    logger.info("Executing service")
     return 1
"""

    mock_patch = ProposedPatch(
        title="Add log to run()",
        problem_description="Service lacks execution logging",
        technical_rationale="Add info log",
        files_affected=["api/service.py"],
        diff_content=valid_diff,
        supporting_evidence_ids=["EV-001"],
        expected_outcome="Service logs executions",
        verification_steps=["pytest"],
        risk_level=PatchRiskLevel.LOW,
    )

    mock_llm = MagicMock(spec=BaseChatModel)
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_patch
    mock_llm.with_structured_output.return_value = mock_structured

    graph = create_remediation_graph(llm=mock_llm)

    state: RemediationState = {
        "incident_id": "inc-rem-001",
        "incident_title": "Silent Service Failure",
        "project_name": "MockApp",
        "project_workspace_path": str(ws),
        "investigation_result": {
            "insufficient_evidence": False,
            "structured_hypotheses": [
                {
                    "root_cause_title": "Missing telemetry in api/service.py",
                    "technical_explanation": "Defect in service.py",
                    "supporting_evidence_ids": ["EV-001"],
                }
            ],
            "evidence_items": [
                {
                    "evidence_id": "EV-001",
                    "source_reference": "api/service.py:1",
                    "description": "Silent exit in api/service.py",
                }
            ],
        },
        "errors": [],
    }

    final_state = graph.invoke(state)

    assert final_state["eligibility"]["status"] == "eligible"
    assert final_state["proposed_patch"] is not None
    assert final_state["proposed_patch"]["title"] == "Add log to run()"
    assert final_state["validation_result"]["is_valid"] is True
    assert final_state["risk_assessment"] is not None
    assert final_state["execution_status"] == "completed"


def test_remediation_workflow_terminates_early_when_ineligible():
    mock_llm = MagicMock(spec=BaseChatModel)
    graph = create_remediation_graph(llm=mock_llm)

    state: RemediationState = {
        "incident_id": "inc-rem-002",
        "incident_title": "Network Partition",
        "investigation_result": {
            "insufficient_evidence": False,
            "structured_hypotheses": [{"root_cause_title": "Datacenter network partition in us-west"}],
            "evidence_items": [],
        },
        "errors": [],
    }

    final_state = graph.invoke(state)

    assert final_state["eligibility"]["status"] == "infrastructure_issue"
    assert final_state.get("proposed_patch") is None
    # Verify LLM was not called since workflow terminated early
    mock_llm.with_structured_output.assert_not_called()


def test_remediation_workflow_handles_llm_failure(tmp_path):
    ws = tmp_path / "mock_app"
    ws.mkdir()
    (ws / "main.py").write_text("x = 1\n", encoding="utf-8")

    mock_llm = MagicMock(spec=BaseChatModel)
    mock_structured = MagicMock()
    mock_structured.invoke.side_effect = RuntimeError("Model provider 500 error")
    mock_llm.with_structured_output.return_value = mock_structured

    graph = create_remediation_graph(llm=mock_llm)

    state: RemediationState = {
        "incident_id": "inc-rem-003",
        "incident_title": "Error in main.py",
        "project_workspace_path": str(ws),
        "investigation_result": {
            "insufficient_evidence": False,
            "structured_hypotheses": [{"root_cause_title": "Bug in main.py"}],
            "evidence_items": [{"evidence_id": "EV-001", "source_reference": "main.py:1", "description": "Crash"}],
        },
        "errors": [],
    }

    final_state = graph.invoke(state)

    assert final_state["execution_status"] == "failed"
    assert final_state.get("proposed_patch") is None
    assert len(final_state["errors"]) > 0
    assert "Model provider 500 error" in final_state["errors"][-1]

