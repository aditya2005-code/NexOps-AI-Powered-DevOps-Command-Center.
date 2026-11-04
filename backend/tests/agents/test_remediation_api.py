import uuid
from datetime import datetime, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agents.runtime.remediation_executor import IncidentRemediationExecutor
from app.agents.schemas.remediation import (
    PatchRiskLevel,
    ProposedPatch,
    RemediationEligibility,
    RemediationEligibilityStatus,
    RemediationResponse,
)
from app.models.code_patch import CodePatch
from app.models.incident import IncidentSeverity, IncidentStatus
from app.repositories import CodePatchRepository, IncidentRepository, ProjectRepository
from app.schemas.code_patch import CodePatchCreate
from app.schemas.incident import IncidentCreate
from app.schemas.project import ProjectCreate


def test_remediate_endpoint_success(client_with_db: TestClient, db_session: Session):
    project = ProjectRepository.create(
        db_session,
        ProjectCreate(name="Core API", environment="production"),
    )
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=project.id,
            title="Gateway Timeout in client.py",
            description="client.py timeout",
            severity=IncidentSeverity.CRITICAL,
            status=IncidentStatus.OPEN,
        ),
    )
    db_session.commit()

    mock_resp = RemediationResponse(
        incident_id=incident.id,
        execution_id=uuid.uuid4(),
        patch_id=uuid.uuid4(),
        patch_hash="a" * 64,
        eligibility=RemediationEligibility(
            status=RemediationEligibilityStatus.ELIGIBLE,
            reason="Code defect in client.py",
            eligible_files=["client.py"],
        ),
        proposed_patch=ProposedPatch(
            title="Increase timeout in client.py",
            problem_description="3s timeout is too short",
            technical_rationale="Change timeout to 15s",
            files_affected=["client.py"],
            diff_content="--- a/client.py\n+++ b/client.py\n@@ -1,1 +1,1 @@\n-timeout=3\n+timeout=15\n",
            expected_outcome="No timeouts",
            risk_level=PatchRiskLevel.LOW,
        ),
        execution_status="COMPLETED",
        duration_seconds=0.35,
        created_at=datetime.now(timezone.utc),
    )

    with patch.object(IncidentRemediationExecutor, "execute", return_value=mock_resp):
        response = client_with_db.post(f"/api/v1/incidents/{incident.id}/remediate")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["incident_id"] == str(incident.id)
        assert data["data"]["eligibility"]["status"] == "eligible"
        assert data["data"]["proposed_patch"]["title"] == "Increase timeout in client.py"


def test_remediate_endpoint_not_found(client_with_db: TestClient):
    random_id = uuid.uuid4()
    response = client_with_db.post(f"/api/v1/incidents/{random_id}/remediate")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert f"Incident with ID '{random_id}' not found" in data["message"]


def test_list_incident_patches_endpoint(client_with_db: TestClient, db_session: Session):
    project = ProjectRepository.create(
        db_session,
        ProjectCreate(name="Auth App", environment="production"),
    )
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=project.id,
            title="Session bug in auth.py",
        ),
    )
    db_session.commit()

    patch1 = CodePatchRepository.create(
        db_session,
        CodePatchCreate(
            incident_id=incident.id,
            title="Fix session null check",
            patch_content="--- a/auth.py\n+++ b/auth.py\n@@ -1,1 +1,2 @@\n+check\n",
        ),
    )
    db_session.commit()

    response = client_with_db.get(f"/api/v1/incidents/{incident.id}/patches")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == str(patch1.id)
    assert data["data"][0]["title"] == "Fix session null check"
    assert data["data"][0]["patch_hash"] == patch1.patch_hash


def test_get_patch_detail_endpoint(client_with_db: TestClient, db_session: Session):
    project = ProjectRepository.create(
        db_session,
        ProjectCreate(name="Payment App", environment="production"),
    )
    incident = IncidentRepository.create(
        db_session,
        IncidentCreate(
            project_id=project.id,
            title="Payment bug in pay.py",
        ),
    )
    db_session.commit()

    diff_str = "--- a/pay.py\n+++ b/pay.py\n@@ -1,1 +1,2 @@\n+new line\n"
    created_patch = CodePatchRepository.create(
        db_session,
        CodePatchCreate(
            incident_id=incident.id,
            title="Add retry logic to pay()",
            patch_content=diff_str,
        ),
    )
    db_session.commit()

    response = client_with_db.get(f"/api/v1/patches/{created_patch.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == str(created_patch.id)
    assert data["data"]["patch_hash"] == CodePatch.compute_sha256(diff_str)
    assert data["data"]["status"] == "pending_approval"


def test_get_patch_detail_not_found(client_with_db: TestClient):
    random_id = uuid.uuid4()
    response = client_with_db.get(f"/api/v1/patches/{random_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert f"Code patch with ID '{random_id}' not found" in data["message"]

