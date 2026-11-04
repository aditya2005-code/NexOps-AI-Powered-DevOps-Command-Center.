import subprocess
import tempfile
import uuid
from pathlib import Path
import pytest
from sqlalchemy.orm import Session

from app.agents.application.approval_service import ApprovalService
from app.agents.application.exceptions import (
    ApprovalIntegrityError,
    PatchAlreadyAppliedError,
    PatchAlreadyRejectedError,
    PatchApplicationError,
    PatchConcurrentModificationError,
    PatchNotApprovedError,
    SecurityViolationError,
)
from app.agents.application.patch_application_service import PatchApplicationService
from app.core.config import Settings, settings
from app.models.code_patch import CodePatch
from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.models.project import Project
from app.repositories import AuditLogRepository, CodePatchRepository


@pytest.fixture
def temp_git_project(db_session: Session):
    """Fixture providing a temporary real Git project with registered Project and Incident records."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir).resolve()

        # Initialize Git repo
        subprocess.run(["git", "init"], cwd=str(repo_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@nexops.local"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "NexOps Test"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
        )

        # Create target file to be patched
        gateway_file = repo_path / "gateway.py"
        gateway_content = (
            "import requests\n\n"
            "def forward_request(url):\n"
            "    return requests.get(url)\n"
        )
        gateway_file.write_text(gateway_content, encoding="utf-8")

        subprocess.run(["git", "add", "gateway.py"], cwd=str(repo_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit for gateway"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
        )

        head_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_path),
            text=True,
        ).strip()

        proj_name = f"git-proj-{uuid.uuid4().hex[:6]}"
        proj = Project(
            name=proj_name,
            environment="development",
            status="active",
        )
        db_session.add(proj)
        db_session.commit()
        db_session.refresh(proj)

        inc = Incident(
            project_id=proj.id,
            title="Gateway Timeout Incident",
            severity=IncidentSeverity.HIGH,
            status=IncidentStatus.OPEN,
        )
        db_session.add(inc)
        db_session.commit()
        db_session.refresh(inc)

        yield repo_path, head_sha, proj, inc


@pytest.fixture
def valid_diff() -> str:
    return (
        "--- a/gateway.py\n"
        "+++ b/gateway.py\n"
        "@@ -3,2 +3,3 @@\n"
        " def forward_request(url):\n"
        "-    return requests.get(url)\n"
        "+    # Added timeout parameter\n"
        "+    return requests.get(url, timeout=30)\n"
    )


def test_successful_patch_application_in_isolated_worktree(
    monkeypatch,
    db_session: Session,
    temp_git_project,
    valid_diff: str,
):
    """Verify that an approved patch applies cleanly in an isolated worktree and preserves primary workspace."""
    repo_path, head_sha, proj, inc = temp_git_project

    # Configure workspace resolution to return temp repo path
    monkeypatch.setattr(
        Settings,
        "get_project_workspace_path",
        lambda self, p: repo_path,
    )

    # 1. Create patch record
    patch_hash = CodePatch.compute_sha256(valid_diff)
    patch = CodePatch(
        incident_id=inc.id,
        title="Fix Gateway Timeout by setting 30s timeout",
        patch_content=valid_diff,
        patch_hash=patch_hash,
        base_commit=head_sha,
        status="pending_approval",
    )
    db_session.add(patch)
    db_session.commit()
    db_session.refresh(patch)

    # Record primary repo file state before application
    primary_gateway = repo_path / "gateway.py"
    primary_before = primary_gateway.read_text(encoding="utf-8")

    # 2. Approve patch
    ApprovalService.approve_patch(
        db=db_session,
        patch_id=patch.id,
        comment="Approved for isolated patch application",
        authenticated_user="engineer_lead",
    )
    db_session.refresh(patch)
    assert patch.status == "approved"

    # 3. Apply patch
    result = PatchApplicationService.apply_patch(
        db=db_session,
        patch_id=patch.id,
        authenticated_user="engineer_lead",
    )

    # 4. Verify result object
    assert result.status == "applied"
    assert result.patch_id == patch.id
    assert "gateway.py" in result.modified_files
    assert result.lines_added == 2
    assert result.lines_removed == 1
    assert result.is_hash_valid is True

    # 5. Verify database state
    db_session.refresh(patch)
    assert patch.status == "applied"

    # 6. CRITICAL VERIFICATION: Primary repository workspace remains 100% UNCHANGED
    primary_after = primary_gateway.read_text(encoding="utf-8")
    assert primary_before == primary_after
    assert "timeout=30" not in primary_after  # Main branch workspace untouched

    # 7. Verify audit logs
    logs = AuditLogRepository.get_by_resource(
        db_session,
        resource_type="code_patch",
        resource_id=patch.id,
    )
    assert any(log.action == "patch_application_succeeded" for log in logs)


def test_unapproved_pending_patch_cannot_be_applied(
    monkeypatch,
    db_session: Session,
    temp_git_project,
    valid_diff: str,
):
    """Test that applying a patch in 'pending_approval' status is strictly rejected."""
    repo_path, head_sha, _, inc = temp_git_project
    monkeypatch.setattr(Settings, "get_project_workspace_path", lambda self, p: repo_path)

    patch = CodePatch(
        incident_id=inc.id,
        title="Unapproved patch",
        patch_content=valid_diff,
        patch_hash=CodePatch.compute_sha256(valid_diff),
        base_commit=head_sha,
        status="pending_approval",
    )
    db_session.add(patch)
    db_session.commit()

    with pytest.raises(PatchNotApprovedError):
        PatchApplicationService.apply_patch(db=db_session, patch_id=patch.id)


def test_rejected_patch_cannot_be_applied(
    monkeypatch,
    db_session: Session,
    temp_git_project,
    valid_diff: str,
):
    """Test that applying a rejected patch is strictly rejected."""
    repo_path, head_sha, _, inc = temp_git_project
    monkeypatch.setattr(Settings, "get_project_workspace_path", lambda self, p: repo_path)

    patch = CodePatch(
        incident_id=inc.id,
        title="Rejected patch",
        patch_content=valid_diff,
        patch_hash=CodePatch.compute_sha256(valid_diff),
        base_commit=head_sha,
        status="pending_approval",
    )
    db_session.add(patch)
    db_session.commit()

    ApprovalService.reject_patch(db=db_session, patch_id=patch.id, reason="Rejected by QA")

    with pytest.raises(PatchAlreadyRejectedError):
        PatchApplicationService.apply_patch(db=db_session, patch_id=patch.id)


def test_modified_patch_after_approval_rejected(
    monkeypatch,
    db_session: Session,
    temp_git_project,
    valid_diff: str,
):
    """Test that if patch content changes after approval, application is rejected due to hash mismatch."""
    repo_path, head_sha, _, inc = temp_git_project
    monkeypatch.setattr(Settings, "get_project_workspace_path", lambda self, p: repo_path)

    patch = CodePatch(
        incident_id=inc.id,
        title="Tampered after approval",
        patch_content=valid_diff,
        patch_hash=CodePatch.compute_sha256(valid_diff),
        base_commit=head_sha,
        status="pending_approval",
    )
    db_session.add(patch)
    db_session.commit()

    ApprovalService.approve_patch(db=db_session, patch_id=patch.id)

    # Tamper with patch content in DB
    tampered_diff = valid_diff + "+# Injected unauthorized line\n"
    patch.patch_content = tampered_diff
    patch.patch_hash = CodePatch.compute_sha256(tampered_diff)
    db_session.commit()

    with pytest.raises(ApprovalIntegrityError) as exc_info:
        PatchApplicationService.apply_patch(db=db_session, patch_id=patch.id)

    assert "Approval hash mismatch" in str(exc_info.value)


def test_failing_patch_marks_patch_as_failed(
    monkeypatch,
    db_session: Session,
    temp_git_project,
):
    """Test that if git apply fails (e.g. malformed context), status transitions to 'failed'."""
    repo_path, head_sha, _, inc = temp_git_project
    monkeypatch.setattr(Settings, "get_project_workspace_path", lambda self, p: repo_path)

    bad_diff = (
        "--- a/gateway.py\n"
        "+++ b/gateway.py\n"
        "@@ -99,2 +99,2 @@\n"
        "-def nonexistent():\n"
        "+def replaced():\n"
    )
    patch = CodePatch(
        incident_id=inc.id,
        title="Failing patch",
        patch_content=bad_diff,
        patch_hash=CodePatch.compute_sha256(bad_diff),
        base_commit=head_sha,
        status="pending_approval",
    )
    db_session.add(patch)
    db_session.commit()

    ApprovalService.approve_patch(db=db_session, patch_id=patch.id)

    with pytest.raises(PatchApplicationError):
        PatchApplicationService.apply_patch(db=db_session, patch_id=patch.id)

    db_session.refresh(patch)
    assert patch.status == "failed"


def test_stale_applying_patch_recovery(db_session: Session, temp_git_project, valid_diff: str):
    """Test that patches stuck in 'applying' state can be recovered."""
    _, head_sha, _, inc = temp_git_project

    patch = CodePatch(
        incident_id=inc.id,
        title="Stuck patch",
        patch_content=valid_diff,
        patch_hash=CodePatch.compute_sha256(valid_diff),
        base_commit=head_sha,
        status="applying",
    )
    db_session.add(patch)
    db_session.commit()

    # Recover with max_age_seconds=0
    recovered = PatchApplicationService.recover_stale_applying_patches(db=db_session, max_age_seconds=0)
    assert recovered == 1

    db_session.refresh(patch)
    assert patch.status == "failed"
