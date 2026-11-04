import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.orm import Session

from app.agents.runtime.remediation_executor import IncidentRemediationExecutor
from app.agents.schemas.remediation import PatchRiskLevel, ProposedPatch
from app.models.incident import IncidentSeverity, IncidentStatus
from app.repositories import IncidentRepository, ProjectRepository
from app.schemas.incident import IncidentCreate
from app.schemas.project import ProjectCreate


def compute_workspace_hashes(workspace_dir: Path) -> dict[str, str]:
    """Compute SHA-256 for every file in the workspace directory."""
    hashes = {}
    for p in sorted(workspace_dir.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(workspace_dir)).replace("\\", "/")
            hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes


def setup_test_workspace(tmp_path) -> Path:
    ws = tmp_path / "test_workspace"
    ws.mkdir(parents=True, exist_ok=True)
    src = ws / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "service.py").write_text("def process(x):\n    return x * 2\n", encoding="utf-8")
    (src / "config.json").write_text('{"timeout": 30}\n', encoding="utf-8")
    (ws / "README.md").write_text("# Test Project\n", encoding="utf-8")
    return ws


def setup_incident(db_session: Session) -> tuple:
    project = ProjectRepository.create(
        db_session,
        ProjectCreate(name="Integrity App", environment="production"),
    )
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=project.id,
            title="Integrity Bug in src/service.py",
            description="src/service.py has defect",
            severity=IncidentSeverity.MEDIUM,
            status=IncidentStatus.OPEN,
        ),
    )
    db_session.commit()
    return project, incident


def test_workspace_integrity_successful_patch(db_session: Session, tmp_path, monkeypatch):
    """Verify workspace files are completely unmodified after successful patch generation."""
    ws = setup_test_workspace(tmp_path)
    project, incident = setup_incident(db_session)

    monkeypatch.setattr(
        "app.core.config.Settings.get_project_workspace_path",
        lambda self, p: ws,
    )

    hashes_before = compute_workspace_hashes(ws)

    valid_diff = """--- a/src/service.py
+++ b/src/service.py
@@ -1,2 +1,3 @@
 def process(x):
+    logger.debug("Processing")
     return x * 2
"""
    mock_patch = ProposedPatch(
        title="Add debug log",
        problem_description="Service lacks debug log",
        technical_rationale="Add debug log",
        files_affected=["src/service.py"],
        diff_content=valid_diff,
        supporting_evidence_ids=["EV-001"],
        expected_outcome="Logged",
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
            "structured_hypotheses": [{"root_cause_title": "Defect in src/service.py"}],
            "evidence_items": [{"evidence_id": "EV-001", "source_reference": "src/service.py:1", "description": "err"}],
        },
    )

    hashes_after = compute_workspace_hashes(ws)
    assert hashes_before == hashes_after
    assert response.patch_id is not None


def test_workspace_integrity_invalid_patch(db_session: Session, tmp_path, monkeypatch):
    """Verify workspace is unmodified when generated patch contains syntax errors."""
    ws = setup_test_workspace(tmp_path)
    project, incident = setup_incident(db_session)
    monkeypatch.setattr("app.core.config.Settings.get_project_workspace_path", lambda self, p: ws)

    hashes_before = compute_workspace_hashes(ws)

    # Invalid diff without hunk headers
    invalid_diff = "Invalid patch content with no diff headers"
    mock_patch = ProposedPatch(
        title="Invalid diff",
        problem_description="Bad syntax",
        technical_rationale="None",
        files_affected=["src/service.py"],
        diff_content=invalid_diff,
        expected_outcome="Fails",
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
            "structured_hypotheses": [{"root_cause_title": "Bug in src/service.py"}],
            "evidence_items": [{"evidence_id": "EV-001", "source_reference": "src/service.py:1", "description": "err"}],
        },
    )

    hashes_after = compute_workspace_hashes(ws)
    assert hashes_before == hashes_after
    assert response.execution_status == "FAILED"
    assert response.patch_id is None


def test_workspace_integrity_llm_failure(db_session: Session, tmp_path, monkeypatch):
    """Verify workspace is unmodified when LLM provider throws an exception."""
    ws = setup_test_workspace(tmp_path)
    project, incident = setup_incident(db_session)
    monkeypatch.setattr("app.core.config.Settings.get_project_workspace_path", lambda self, p: ws)

    hashes_before = compute_workspace_hashes(ws)

    mock_llm = MagicMock(spec=BaseChatModel)
    mock_structured = MagicMock()
    mock_structured.invoke.side_effect = RuntimeError("Provider overloaded 503")
    mock_llm.with_structured_output.return_value = mock_structured

    response = IncidentRemediationExecutor.execute(
        db=db_session,
        incident_id=incident.id,
        llm=mock_llm,
        investigation_result_override={
            "insufficient_evidence": False,
            "structured_hypotheses": [{"root_cause_title": "Bug in src/service.py"}],
            "evidence_items": [{"evidence_id": "EV-001", "source_reference": "src/service.py:1", "description": "err"}],
        },
    )

    hashes_after = compute_workspace_hashes(ws)
    assert hashes_before == hashes_after
    assert response.execution_status == "FAILED"
    assert response.patch_id is None


def test_workspace_integrity_diff_validation_failure(db_session: Session, tmp_path, monkeypatch):
    """Verify workspace is unmodified when diff validation fails due to unauthorized files."""
    ws = setup_test_workspace(tmp_path)
    project, incident = setup_incident(db_session)
    monkeypatch.setattr("app.core.config.Settings.get_project_workspace_path", lambda self, p: ws)

    hashes_before = compute_workspace_hashes(ws)

    unauthorized_diff = """--- a/unauthorized.py
+++ b/unauthorized.py
@@ -1,1 +1,2 @@
+hack
"""
    mock_patch = ProposedPatch(
        title="Unauthorized modification",
        problem_description="Touches unauthorized file",
        technical_rationale="None",
        files_affected=["unauthorized.py"],
        diff_content=unauthorized_diff,
        expected_outcome="Fails",
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
            "structured_hypotheses": [{"root_cause_title": "Bug in src/service.py"}],
            "evidence_items": [{"evidence_id": "EV-001", "source_reference": "src/service.py:1", "description": "err"}],
        },
    )

    hashes_after = compute_workspace_hashes(ws)
    assert hashes_before == hashes_after
    assert response.execution_status == "FAILED"
    assert response.patch_id is None


def test_workspace_integrity_persistence_failure(db_session: Session, tmp_path, monkeypatch):
    """Verify workspace is unmodified when database persistence fails."""
    ws = setup_test_workspace(tmp_path)
    project, incident = setup_incident(db_session)
    monkeypatch.setattr("app.core.config.Settings.get_project_workspace_path", lambda self, p: ws)

    hashes_before = compute_workspace_hashes(ws)

    valid_diff = """--- a/src/service.py
+++ b/src/service.py
@@ -1,2 +1,3 @@
 def process(x):
+    pass
     return x * 2
"""
    mock_patch = ProposedPatch(
        title="Valid patch",
        problem_description="Test",
        technical_rationale="Test",
        files_affected=["src/service.py"],
        diff_content=valid_diff,
        expected_outcome="Pass",
        risk_level=PatchRiskLevel.LOW,
    )
    mock_llm = MagicMock(spec=BaseChatModel)
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_patch
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("app.repositories.CodePatchRepository.create", side_effect=Exception("Database connection dead")):
        try:
            IncidentRemediationExecutor.execute(
                db=db_session,
                incident_id=incident.id,
                llm=mock_llm,
                investigation_result_override={
                    "insufficient_evidence": False,
                    "structured_hypotheses": [{"root_cause_title": "Bug in src/service.py"}],
                    "evidence_items": [{"evidence_id": "EV-001", "source_reference": "src/service.py:1", "description": "err"}],
                },
            )
        except Exception:
            pass

    hashes_after = compute_workspace_hashes(ws)
    assert hashes_before == hashes_after

