import subprocess
import tempfile
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.main import app
from app.models.code_patch import CodePatch
from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.models.project import Project


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def api_test_setup(db_session: Session):
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir).resolve()

        subprocess.run(["git", "init"], cwd=str(repo_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "api-test@nexops.local"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "API Test"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
        )

        f = repo_path / "main.py"
        f.write_text("print('hello')\n", encoding="utf-8")
        subprocess.run(["git", "add", "main.py"], cwd=str(repo_path), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo_path), check=True, capture_output=True)

        head_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_path), text=True
        ).strip()

        proj = Project(name=f"api-proj-{uuid.uuid4().hex[:6]}", environment="development")
        db_session.add(proj)
        db_session.commit()

        inc = Incident(project_id=proj.id, title="API Test Incident", severity=IncidentSeverity.MEDIUM)
        db_session.add(inc)
        db_session.commit()

        diff = "--- a/main.py\n+++ b/main.py\n@@ -1,1 +1,2 @@\n print('hello')\n+print('world')\n"
        patch = CodePatch(
            incident_id=inc.id,
            title="Add world print",
            patch_content=diff,
            patch_hash=CodePatch.compute_sha256(diff),
            base_commit=head_sha,
            status="pending_approval",
        )
        db_session.add(patch)
        db_session.commit()
        db_session.refresh(patch)

        yield repo_path, patch


def test_api_approve_and_reject_endpoints(client_with_db: TestClient, api_test_setup):
    """Test POST /api/v1/patches/{patch_id}/approve and history retrieval."""
    _, patch = api_test_setup

    # 1. Check approval before decision -> None
    res = client_with_db.get(f"/api/v1/patches/{patch.id}/approval")
    assert res.status_code == 200
    assert res.json()["data"] is None

    # 2. Approve patch
    res = client_with_db.post(
        f"/api/v1/patches/{patch.id}/approve",
        json={"comment": "Approved via REST API"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["decision"] == "APPROVED"
    assert data["comment"] == "Approved via REST API"

    # 3. Check approval status now returns approval record
    res = client_with_db.get(f"/api/v1/patches/{patch.id}/approval")
    assert res.status_code == 200
    assert res.json()["data"]["decision"] == "APPROVED"

    # 4. Check history
    res = client_with_db.get(f"/api/v1/patches/{patch.id}/approval/history")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 1

    # 5. Approving again returns 409 Conflict
    res = client_with_db.post(f"/api/v1/patches/{patch.id}/approve")
    assert res.status_code == 409


def test_api_apply_patch_endpoint(client_with_db: TestClient, monkeypatch, api_test_setup):
    """Test POST /api/v1/patches/{patch_id}/apply and GET /api/v1/patches/{patch_id}/application."""
    repo_path, patch = api_test_setup
    monkeypatch.setattr(Settings, "get_project_workspace_path", lambda self, p: repo_path)

    # 1. Attempting apply before approval -> 409 Conflict
    res = client_with_db.post(f"/api/v1/patches/{patch.id}/apply")
    assert res.status_code == 409

    # 2. Approve patch
    client_with_db.post(f"/api/v1/patches/{patch.id}/approve")

    # 3. Apply patch
    res = client_with_db.post(f"/api/v1/patches/{patch.id}/apply")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "applied"
    assert "main.py" in data["modified_files"]

    # 4. Retrieve application status
    res = client_with_db.get(f"/api/v1/patches/{patch.id}/application")
    assert res.status_code == 200
    app_data = res.json()["data"]
    assert app_data["status"] == "applied"
    assert "main.py" in app_data["modified_files"]
    assert app_data["is_hash_valid"] is True
