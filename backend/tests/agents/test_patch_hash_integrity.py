import hashlib
import uuid
import pytest
from sqlalchemy.orm import Session

from app.models.approval import Approval, ApprovalDecision
from app.models.code_patch import CodePatch
from app.repositories import CodePatchRepository, IncidentRepository, ProjectRepository
from app.schemas.code_patch import CodePatchCreate
from app.schemas.incident import IncidentCreate
from app.schemas.project import ProjectCreate


def test_patch_hash_computed_from_exact_bytes():
    content = "--- a/main.py\n+++ b/main.py\n@@ -1,1 +1,2 @@\n+print('hello')\n"
    expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    computed = CodePatch.compute_sha256(content)
    assert computed == expected_hash
    assert len(computed) == 64


def test_empty_patch_hash_raises_error():
    """Verify that an empty or whitespace patch cannot compute a valid hash."""
    with pytest.raises(ValueError, match="cannot be empty"):
        CodePatch.compute_sha256("")

    with pytest.raises(ValueError, match="cannot be empty"):
        CodePatch.compute_sha256("   \n\t  ")


def test_persisted_patch_matches_hash_and_retrieval_verification(db_session: Session):
    project = ProjectRepository.create(
        db_session,
        ProjectCreate(name="Hash Integrity App", environment="production"),
    )
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=project.id,
            title="Hash Incident",
        ),
    )
    db_session.commit()

    content = "--- a/app.py\n+++ b/app.py\n@@ -1,1 +1,2 @@\n+safe_change()\n"
    patch_record = CodePatchRepository.create(
        db_session,
        CodePatchCreate(
            incident_id=incident.id,
            title="Safe fix",
            patch_content=content,
        ),
    )
    db_session.commit()

    # Verify persisted content matches hashed content
    assert patch_record.patch_hash == CodePatch.compute_sha256(content)
    assert CodePatchRepository.verify_patch_hash(patch_record) is True


def test_modified_content_invalidates_hash(db_session: Session):
    """Verify that if patch_content is altered/tampered in database, verify_patch_hash returns False."""
    project = ProjectRepository.create(
        db_session,
        ProjectCreate(name="Tamper App", environment="production"),
    )
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=project.id,
            title="Tamper Incident",
        ),
    )
    db_session.commit()

    original_content = "--- a/app.py\n+++ b/app.py\n@@ -1,1 +1,2 @@\n+safe_fix()\n"
    patch_record = CodePatchRepository.create(
        db_session,
        CodePatchCreate(
            incident_id=incident.id,
            title="Tampered patch",
            patch_content=original_content,
        ),
    )
    db_session.commit()

    # Tamper with content directly
    patch_record.patch_content = "--- a/app.py\n+++ b/app.py\n@@ -1,1 +1,2 @@\n+malicious_backdoor()\n"
    db_session.flush()

    # Verification must fail!
    assert CodePatchRepository.verify_patch_hash(patch_record) is False


def test_approval_bound_to_exact_patch_hash(db_session: Session):
    """Verify that an Approval record is cryptographically bound to the patch's hash."""
    project = ProjectRepository.create(
        db_session,
        ProjectCreate(name="Approval App", environment="production"),
    )
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=project.id,
            title="Approval Incident",
        ),
    )
    db_session.commit()

    content = "--- a/auth.py\n+++ b/auth.py\n@@ -1,1 +1,2 @@\n+verify()\n"
    patch_record = CodePatchRepository.create(
        db_session,
        CodePatchCreate(
            incident_id=incident.id,
            title="Approved fix",
            patch_content=content,
        ),
    )
    db_session.commit()

    # Create approval bound to patch_record.patch_hash
    approval = Approval(
        patch_id=patch_record.id,
        patch_hash=patch_record.patch_hash,
        decision=ApprovalDecision.APPROVED,
        reviewer_identifier="security-lead",
        comment="Approved after static analysis",
    )
    db_session.add(approval)
    db_session.commit()

    assert approval.patch_hash == patch_record.patch_hash

    # If patch content changes, it no longer matches approval hash
    tampered_content = "--- a/auth.py\n+++ b/auth.py\n@@ -1,1 +1,2 @@\n+bypass()\n"
    assert CodePatch.compute_sha256(tampered_content) != approval.patch_hash

