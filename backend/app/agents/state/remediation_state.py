from typing import Any, Dict, List, Optional, TypedDict


class RemediationState(TypedDict, total=False):
    """LangGraph state representation for the AI remediation and patch generation workflow."""

    # Incident & Investigation Identifiers
    incident_id: str
    investigation_execution_id: Optional[str]
    project_id: Optional[str]
    project_name: Optional[str]
    project_workspace_path: Optional[str]
    incident_title: str
    incident_description: Optional[str]

    # Investigation Input
    investigation_result: Dict[str, Any]

    # Eligibility Evaluation
    eligibility: Dict[str, Any]

    # Remediation Planning
    remediation_plan: Optional[Dict[str, Any]]
    target_files: List[str]

    # Authorized Source Code Context
    source_context: List[Dict[str, Any]]
    remediation_context: str

    # Patch Generation, Validation & Risk
    proposed_patch: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    risk_assessment: Optional[Dict[str, Any]]

    # Persistence
    patch_id: Optional[str]
    patch_hash: Optional[str]

    # Lifecycle & Telemetry
    execution_status: str
    errors: List[str]

