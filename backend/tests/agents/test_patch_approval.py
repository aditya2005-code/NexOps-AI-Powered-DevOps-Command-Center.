import uuid
import pytest
from sqlalchemy.orm import Session

from app.agents.application.approval_service import ApprovalService
from app.agents.application.exceptions import (
    AuthenticationRequiredError,
    PatchAlreadyAppliedError,
    PatchAlreadyApprovedError,
    PatchAlreadyRejectedError,
    PatchIntegrityError,
    PatchNotApprovedError,
    PatchNotFoundError,
)
from app.core.config import settings
from app.models.approval import ApprovalDecision
from app.models.code_patch import CodePatch
from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.models.project import Project
from app.repositories import AuditLogRepository, CodePatchRepository


@pytest.fixture
def test_project(db_session: Session) -> Project:
    proj = Project(
        name=f"test-proj-{uuid.uuid4().hex[:6]}",
        environment="development",
        status="active",
    )
    db_session.add(proj)
    db_session.commit()
    db_session.refresh(proj)
    return proj


@pytest.fixture
def test_incident(db_session: Session, test_project: Project) -> Incident:
    inc = Incident(
        project_id=test_project.id,
        title="Test Incident for Approval",
        severity=IncidentSeverity.HIGH,
        status=IncidentStatus.OPEN,
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)
    return inc


@pytest.fixture
def sample_patch(db_session: Session, test_incident: Incident) -> CodePatch:
    diff_content = (
        "--- a/service.py\n"
        "+++ b/service.py\n"
        "@@ -1,2 +1,3 @@\n"
        " def handle():\n"
        "+    # Fix applied\n"
        "     return True\n"
    )
    patch_hash = CodePatch.compute_sha256(diff_content)
    patch = CodePatch(
        incident_id=test_incident.id,
        title="Fix Gateway Timeout",
        patch_content=diff_content,
        patch_hash=patch_hash,
        base_commit="abc1234",
        status="pending_approval",
    )
    db_session.add(patch)
    db_session.commit()
    db_session.refresh(patch)
    return patch


def test_valid_patch_approval(db_session: Session, sample_patch: CodePatch):
    """Test approving a pending patch verifies hash and transitions status to 'approved'."""
    resp = ApprovalService.approve_patch(
        db=db_session,
        patch_id=sample_patch.id,
        comment="Looks good to me, reviewed code diff.",
        authenticated_user="engineer_alice",
    )

    assert resp.patch_id == sample_patch.id
    assert resp.decision == ApprovalDecision.APPROVED
    assert resp.patch_hash == sample_patch.patch_hash
    assert resp.reviewer_identifier == "engineer_alice"
    assert resp.comment == "Looks good to me, reviewed code diff."

    # Verify DB state
    db_session.refresh(sample_patch)
    assert sample_patch.status == "approved"

    # Verify audit log
    logs = AuditLogRepository.get_by_resource(
        db_session,
        resource_type="code_patch",
        resource_id=sample_patch.id,
    )
    assert any(log.action == "approval_granted" for log in logs)


def test_valid_patch_rejection(db_session: Session, sample_patch: CodePatch):
    """Test rejecting a pending patch transitions status to 'rejected'."""
    resp = ApprovalService.reject_patch(
        db=db_session,
        patch_id=sample_patch.id,
        reason="Does not address root cause completely.",
        authenticated_user="engineer_bob",
    )

    assert resp.decision == ApprovalDecision.REJECTED
    assert resp.comment == "Does not address root cause completely."

    db_session.refresh(sample_patch)
    assert sample_patch.status == "rejected"

    logs = AuditLogRepository.get_by_resource(
        db_session,
        resource_type="code_patch",
        resource_id=sample_patch.id,
    )
    assert any(log.action == "approval_rejected" for log in logs)


def test_approve_unknown_patch_raises_not_found(db_session: Session):
    """Test approving a non-existent patch raises PatchNotFoundError."""
    random_id = uuid.uuid4()
    with pytest.raises(PatchNotFoundError):
        ApprovalService.approve_patch(db=db_session, patch_id=random_id)


def test_approve_already_approved_patch_raises_error(db_session: Session, sample_patch: CodePatch):
    """Test approving an already approved patch raises PatchAlreadyApprovedError."""
    ApprovalService.approve_patch(db=db_session, patch_id=sample_patch.id)

    with pytest.raises(PatchAlreadyApprovedError):
        ApprovalService.approve_patch(db=db_session, patch_id=sample_patch.id)


def test_approve_already_rejected_patch_raises_error(db_session: Session, sample_patch: CodePatch):
    """Test approving a rejected patch raises PatchAlreadyRejectedError."""
    ApprovalService.reject_patch(db=db_session, patch_id=sample_patch.id)

    with pytest.raises(PatchAlreadyRejectedError):
        ApprovalService.approve_patch(db=db_session, patch_id=sample_patch.id)


def test_reject_already_approved_patch_raises_error(db_session: Session, sample_patch: CodePatch):
    """Test rejecting an already approved patch raises PatchAlreadyApprovedError."""
    ApprovalService.approve_patch(db=db_session, patch_id=sample_patch.id)

    with pytest.raises(PatchAlreadyApprovedError):
        ApprovalService.reject_patch(db=db_session, patch_id=sample_patch.id)


def test_patch_hash_tampering_rejected_at_approval(db_session: Session, sample_patch: CodePatch):
    """Test that if patch content was altered in DB so hash does not match, approval fails."""
    # Tamper content directly in DB without updating patch_hash
    sample_patch.patch_content = sample_patch.patch_content + "\n# Malicious injected code"
    db_session.commit()

    with pytest.raises(PatchIntegrityError) as exc_info:
        ApprovalService.approve_patch(db=db_session, patch_id=sample_patch.id)

    assert "integrity check failed" in str(exc_info.value).lower()


def test_approval_history_tracking(db_session: Session, sample_patch: CodePatch):
    """Test retrieval of approval history."""
    ApprovalService.approve_patch(
        db=db_session,
        patch_id=sample_patch.id,
        comment="Approved initial version",
        authenticated_user="lead_dev",
    )

    history = ApprovalService.get_approval_history(db=db_session, patch_id=sample_patch.id)
    assert len(history) == 1
    assert history[0].patch_id == sample_patch.id
    assert history[0].decision == ApprovalDecision.APPROVED
    assert history[0].reviewer_identifier == "lead_dev"


def test_production_auth_requirement(monkeypatch, db_session: Session, sample_patch: CodePatch):
    """Test that in production mode, approval without authenticated identity is strictly rejected."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "DEV_APPROVAL_ENABLED", False)

    with pytest.raises(AuthenticationRequiredError):
        ApprovalService.approve_patch(
            db=db_session,
            patch_id=sample_patch.id,
            authenticated_user=None,
        )

