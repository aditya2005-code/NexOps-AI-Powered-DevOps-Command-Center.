import re
from typing import Any, Dict, List
from app.agents.schemas.remediation import (
    RemediationEligibility,
    RemediationEligibilityStatus,
)
from app.agents.state.remediation_state import RemediationState

INFRA_KEYWORDS = [
    "network partition",
    "hardware failure",
    "cloud provider outage",
    "datacenter",
    "node eviction",
    "disk full",
    "power loss",
    "carrier loss",
]

CONFIG_KEYWORDS = [
    "missing environment variable",
    "expired certificate",
    "expired token",
    "invalid credentials",
    "configuration file missing",
    "misconfigured dns",
]


def evaluate_remediation_eligibility_node(state: RemediationState) -> Dict[str, Any]:
    """Node: Evaluates whether investigation findings justify an automated code-level remediation."""
    inv = state.get("investigation_result", {})
    workspace = state.get("project_workspace_path")
    evidence_items: List[Dict[str, Any]] = inv.get("evidence_items", [])
    hypotheses: List[Any] = inv.get("structured_hypotheses", []) or inv.get("hypotheses", [])

    # 1. Check for insufficient evidence flag or empty hypotheses
    if inv.get("insufficient_evidence") or not hypotheses:
        eligibility = RemediationEligibility(
            status=RemediationEligibilityStatus.INSUFFICIENT_EVIDENCE,
            reason="Investigation has insufficient technical evidence or hypotheses to justify code modification.",
            recommended_action="Execute supplemental diagnostic queries or inspect service logs manually.",
        )
        return {"eligibility": eligibility.model_dump(), "target_files": []}

    # 2. Check primary hypothesis for infrastructure or hardware issues
    primary_hyp = (
        hypotheses[0].get("root_cause_title", "")
        if isinstance(hypotheses[0], dict)
        else str(hypotheses[0])
    ).lower()

    if any(kw in primary_hyp for kw in INFRA_KEYWORDS):
        eligibility = RemediationEligibility(
            status=RemediationEligibilityStatus.INFRASTRUCTURE_ISSUE,
            reason=f"Root cause points to external infrastructure or platform outage: {primary_hyp}",
            recommended_action="Triage with cloud/infrastructure provider or reboot platform nodes.",
        )
        return {"eligibility": eligibility.model_dump(), "target_files": []}

    # 3. Check for pure configuration / credentials issue
    if any(kw in primary_hyp for kw in CONFIG_KEYWORDS):
        eligibility = RemediationEligibility(
            status=RemediationEligibilityStatus.CONFIGURATION_ISSUE,
            reason=f"Root cause relates to environment configuration or credentials: {primary_hyp}",
            recommended_action="Update deployment secrets or environment variables in secrets manager.",
        )
        return {"eligibility": eligibility.model_dump(), "target_files": []}

    # 4. Check for workspace configuration
    if not workspace:
        eligibility = RemediationEligibility(
            status=RemediationEligibilityStatus.UNSUPPORTED_REMEDIATION,
            reason="Project workspace is not configured or mounted on disk for code inspection.",
            recommended_action="Configure PROJECT_WORKSPACE_MAPPING in environment settings.",
        )
        return {"eligibility": eligibility.model_dump(), "target_files": []}

    # 5. Extract target code files from evidence and hypotheses
    target_files: List[str] = []
    file_pattern = re.compile(r"([a-zA-Z0-9_\-./]+\.(?:py|ts|js|jsx|tsx|go|java|rs|json|yaml|yml))")

    for ev in evidence_items:
        ref = ev.get("source_reference") or ""
        desc = ev.get("description") or ""
        for text in (ref, desc):
            matches = file_pattern.findall(text)
            for m in matches:
                cleaned = m.strip().lstrip("/").replace("\\", "/")
                if not cleaned.startswith(".git") and "test" not in cleaned.lower():
                    if cleaned not in target_files:
                        target_files.append(cleaned)

    # Check hypotheses text for filenames as well
    for m in file_pattern.findall(primary_hyp):
        cleaned = m.strip().lstrip("/").replace("\\", "/")
        if cleaned not in target_files:
            target_files.append(cleaned)

    if not target_files:
        eligibility = RemediationEligibility(
            status=RemediationEligibilityStatus.NO_CODE_CHANGE_REQUIRED,
            reason="No specific source code files were implicated as defect origins in the investigation.",
            recommended_action="Verify service runtime telemetry and external dependencies.",
        )
        return {"eligibility": eligibility.model_dump(), "target_files": []}

    eligibility = RemediationEligibility(
        status=RemediationEligibilityStatus.ELIGIBLE,
        reason=f"Investigation identifies code defect in {', '.join(target_files[:3])}.",
        recommended_action="Construct remediation plan and generate candidate patch.",
        eligible_files=target_files[:5],
    )
    return {"eligibility": eligibility.model_dump(), "target_files": target_files[:5]}

