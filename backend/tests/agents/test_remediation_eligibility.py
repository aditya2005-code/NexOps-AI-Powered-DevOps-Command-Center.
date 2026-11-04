from app.agents.nodes.remediation.evaluate_eligibility import evaluate_remediation_eligibility_node
from app.agents.schemas.remediation import RemediationEligibilityStatus
from app.agents.state.remediation_state import RemediationState


def test_remediation_eligibility_eligible():
    state: RemediationState = {
        "project_workspace_path": "/workspace/project",
        "investigation_result": {
            "insufficient_evidence": False,
            "structured_hypotheses": [
                {
                    "root_cause_title": "Uncaught ValueError in src/api/checkout.py",
                    "technical_explanation": "Missing exception handler in checkout.py",
                }
            ],
            "evidence_items": [
                {
                    "evidence_id": "EV-001",
                    "source_reference": "src/api/checkout.py:42",
                    "description": "ValueError thrown in src/api/checkout.py",
                }
            ],
        },
    }

    result = evaluate_remediation_eligibility_node(state)
    eligibility = result["eligibility"]
    assert eligibility["status"] == RemediationEligibilityStatus.ELIGIBLE
    assert "src/api/checkout.py" in result["target_files"]


def test_remediation_eligibility_insufficient_evidence():
    state: RemediationState = {
        "project_workspace_path": "/workspace/project",
        "investigation_result": {
            "insufficient_evidence": True,
            "structured_hypotheses": [],
            "evidence_items": [],
        },
    }

    result = evaluate_remediation_eligibility_node(state)
    eligibility = result["eligibility"]
    assert eligibility["status"] == RemediationEligibilityStatus.INSUFFICIENT_EVIDENCE
    assert len(result["target_files"]) == 0


def test_remediation_eligibility_infrastructure_issue():
    state: RemediationState = {
        "project_workspace_path": "/workspace/project",
        "investigation_result": {
            "insufficient_evidence": False,
            "structured_hypotheses": [
                {"root_cause_title": "Cloud provider outage in us-east-1 datacenter"}
            ],
            "evidence_items": [{"evidence_id": "EV-001", "description": "AWS outage"}],
        },
    }

    result = evaluate_remediation_eligibility_node(state)
    assert result["eligibility"]["status"] == RemediationEligibilityStatus.INFRASTRUCTURE_ISSUE


def test_remediation_eligibility_configuration_issue():
    state: RemediationState = {
        "project_workspace_path": "/workspace/project",
        "investigation_result": {
            "insufficient_evidence": False,
            "structured_hypotheses": [
                {"root_cause_title": "Missing environment variable DATABASE_URL"}
            ],
            "evidence_items": [{"evidence_id": "EV-001", "description": "KeyError DATABASE_URL"}],
        },
    }

    result = evaluate_remediation_eligibility_node(state)
    assert result["eligibility"]["status"] == RemediationEligibilityStatus.CONFIGURATION_ISSUE


def test_remediation_eligibility_missing_workspace():
    state: RemediationState = {
        "project_workspace_path": None,
        "investigation_result": {
            "insufficient_evidence": False,
            "structured_hypotheses": [{"root_cause_title": "Bug in code"}],
            "evidence_items": [{"evidence_id": "EV-001", "description": "app.py error"}],
        },
    }

    result = evaluate_remediation_eligibility_node(state)
    assert result["eligibility"]["status"] == RemediationEligibilityStatus.UNSUPPORTED_REMEDIATION

