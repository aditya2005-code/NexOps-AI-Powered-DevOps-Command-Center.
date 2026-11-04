from unittest.mock import MagicMock
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.orm import Session

from app.agents.runtime.remediation_executor import IncidentRemediationExecutor
from app.agents.schemas.remediation import PatchRiskLevel, ProposedPatch
from app.models.agent_execution import AgentExecutionStatus, AgentType
from app.models.code_patch import CodePatch
from app.models.incident import IncidentSeverity, IncidentStatus
from app.repositories import (
    AgentExecutionRepository,
    CodePatchRepository,
    IncidentRepository,
    ProjectRepository,
)
from app.schemas.incident import IncidentCreate
from app.schemas.project import ProjectCreate


def test_remediation_executor_creates_code_patch_and_audit(
    db_session: Session, tmp_path, monkeypatch
):
    ws = tmp_path / "billing_service"
    ws.mkdir()
    (ws / "calc.py").write_text("def tax(p):\n    return p * 0.1\n", encoding="utf-8")

    project = ProjectRepository.create(
        db_session,
        ProjectCreate(name="Billing Service", environment="production"),
    )
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=project.id,
            title="Tax calculation rounding bug in calc.py",
            description="calc.py does not round tax to 2 decimal places",
            severity=IncidentSeverity.HIGH,
            status=IncidentStatus.OPEN,
        ),
    )
    db_session.commit()

    # Configure workspace for project
    monkeypatch.setattr(
        "app.core.config.Settings.get_project_workspace_path",
        lambda self, p: ws,
    )

    diff = """--- a/calc.py
+++ b/calc.py
@@ -1,2 +1,2 @@
 def tax(p):
-    return p * 0.1
+    return round(p * 0.1, 2)
"""

    mock_patch = ProposedPatch(
        title="Round tax calculation to 2 decimal places",
        problem_description="Floating point precision errors in tax()",
        technical_rationale="Use standard round()",
        files_affected=["calc.py"],
        diff_content=diff,
        supporting_evidence_ids=["EV-001"],
        expected_outcome="Accurate financial calculations",
        verification_steps=["pytest"],
        risk_level=PatchRiskLevel.LOW,
    )

    mock_llm = MagicMock(spec=BaseChatModel)
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_patch
    mock_llm.with_structured_output.return_value = mock_structured

    response = IncidentRemediationExecutor.execute(
        db=db_session,
        incident_id=incident.id,
        llm=mock_llm,
        investigation_result_override={
            "insufficient_evidence": False,
            "structured_hypotheses": [
                {
                    "root_cause_title": "Floating point precision bug in calc.py",
                    "technical_explanation": "Defect in calc.py",
                    "supporting_evidence_ids": ["EV-001"],
                }
            ],
            "evidence_items": [
                {
                    "evidence_id": "EV-001",
                    "source_reference": "calc.py:2",
                    "description": "calc.py unrounded float",
                }
            ],
        },
    )

    assert response.incident_id == incident.id
    assert response.execution_status == AgentExecutionStatus.COMPLETED.value
    assert response.patch_id is not None
    assert response.patch_hash is not None

    # Verify CodePatch record in database
    patch_record = CodePatchRepository.get_by_id(db_session, response.patch_id)
    assert patch_record is not None
    assert patch_record.title == "Round tax calculation to 2 decimal places"
    assert patch_record.status == "pending_approval"
    assert patch_record.patch_content == diff
    assert CodePatch.compute_sha256(diff) == patch_record.patch_hash
    assert CodePatchRepository.verify_patch_hash(patch_record, diff) is True

    # Verify AgentExecution record
    exec_record = AgentExecutionRepository.get_by_id(db_session, response.execution_id)
    assert exec_record is not None
    assert exec_record.agent_type == AgentType.FIX_AGENT
    assert exec_record.status == AgentExecutionStatus.COMPLETED
