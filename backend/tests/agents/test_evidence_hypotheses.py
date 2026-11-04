from app.agents.nodes.validate_hypotheses import validate_hypotheses_node
from app.agents.schemas.evidence import (
    EvidenceClassification,
    EvidenceItem,
    EvidenceReliability,
    EvidenceSource,
    RootCauseHypothesis,
)
from app.agents.state import InvestigationState


def test_evidence_item_creation():
    item = EvidenceItem(
        evidence_id="EV-001",
        source=EvidenceSource.LOG,
        description="502 Bad Gateway observed on upstream endpoint /api/v1/auth",
        timestamp="2026-11-04T12:00:00Z",
        source_reference="log:line_104",
        classification=EvidenceClassification.ERROR_LOG,
        reliability=EvidenceReliability.VERIFIED,
    )
    assert item.evidence_id == "EV-001"
    assert item.reliability == EvidenceReliability.VERIFIED
    assert item.source == EvidenceSource.LOG


def test_validate_hypotheses_with_insufficient_evidence():
    """Verify confidence is capped and insufficient_evidence is flagged when evidence is sparse."""
    state: InvestigationState = {
        "collected_evidence": [
            {
                "evidence_id": "EV-001",
                "source": "incident_description",
                "description": "High latency on checkout",
                "classification": "observed_symptom",
                "reliability": "inconclusive",
            }
        ],
        "investigation_result": {
            "structured_hypotheses": [
                {
                    "hypothesis_id": "HYP-001",
                    "root_cause_title": "Database deadlocks in transaction pool",
                    "technical_explanation": "Database threads locked during checkout.",
                    "supporting_evidence_ids": ["EV-001"],
                    "contradicting_evidence_ids": [],
                    "confidence_score": 0.90,  # Unwarranted high confidence
                    "recommended_verification_steps": ["Check pg_stat_activity"],
                }
            ]
        },
    }

    result = validate_hypotheses_node(state)
    assert result["validation_results"]["insufficient_evidence"] is True
    # Confidence must be capped because evidence is inconclusive
    assert result["hypotheses"][0]["confidence_score"] <= 0.25


def test_validate_hypotheses_filters_invalid_evidence_ids():
    """Verify non-existent evidence IDs hallucinated by model are sanitized."""
    state: InvestigationState = {
        "collected_evidence": [
            {
                "evidence_id": "EV-001",
                "source": "log",
                "description": "ConnectionResetError: Connection closed by peer",
                "classification": "error_log",
                "reliability": "verified",
            },
            {
                "evidence_id": "EV-002",
                "source": "source_code",
                "description": "src/gateway.py:15 raises ConnectionResetError",
                "classification": "code_defect",
                "reliability": "verified",
            },
        ],
        "investigation_result": {
            "structured_hypotheses": [
                {
                    "hypothesis_id": "HYP-001",
                    "root_cause_title": "Upstream service terminated TCP socket",
                    "technical_explanation": "Upstream pod killed.",
                    "supporting_evidence_ids": ["EV-999", "EV-888"],  # Hallucinated IDs
                    "confidence_score": 0.80,
                }
            ]
        },
    }

    result = validate_hypotheses_node(state)
    hyp = result["hypotheses"][0]
    # Hallucinated IDs EV-999 and EV-888 should be replaced with valid existing IDs
    assert "EV-999" not in hyp["supporting_evidence_ids"]
    assert "EV-888" not in hyp["supporting_evidence_ids"]
    assert "EV-001" in hyp["supporting_evidence_ids"]
    assert hyp["confidence_score"] >= 0.75


def test_validate_hypotheses_ranks_by_confidence_and_evidence():
    """Verify hypotheses are properly sorted in descending order of confidence."""
    state: InvestigationState = {
        "collected_evidence": [
            {"evidence_id": "EV-001", "reliability": "verified"},
            {"evidence_id": "EV-002", "reliability": "verified"},
            {"evidence_id": "EV-003", "reliability": "verified"},
        ],
        "investigation_result": {
            "structured_hypotheses": [
                {
                    "hypothesis_id": "HYP-001",
                    "root_cause_title": "Low probability DNS issue",
                    "technical_explanation": "DNS query failure",
                    "supporting_evidence_ids": ["EV-001"],
                    "confidence_score": 0.35,
                },
                {
                    "hypothesis_id": "HYP-002",
                    "root_cause_title": "Primary root cause: TCP reset from backend",
                    "technical_explanation": "Socket reset",
                    "supporting_evidence_ids": ["EV-001", "EV-002", "EV-003"],
                    "confidence_score": 0.90,
                },
            ]
        },
    }

    result = validate_hypotheses_node(state)
    ranked = result["hypotheses"]
    assert ranked[0]["hypothesis_id"] == "HYP-002"
    assert ranked[1]["hypothesis_id"] == "HYP-001"

