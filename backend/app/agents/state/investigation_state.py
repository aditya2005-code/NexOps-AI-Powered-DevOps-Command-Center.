from typing import Any, Dict, List, Optional, TypedDict


class InvestigationState(TypedDict, total=False):
    """LangGraph state representation for the incident investigation workflow."""

    # Core Identifiers & Incident Details
    incident_id: str
    project_id: Optional[str]
    incident_title: str
    incident_description: Optional[str]
    incident_severity: str
    incident_status: str
    incident_source: str

    # Project Context & Workspace
    project_name: Optional[str]
    project_environment: Optional[str]
    project_workspace_path: Optional[str]

    # Chronological Event Timeline
    incident_events: List[Dict[str, Any]]

    # Investigation Planning
    investigation_plan: Dict[str, Any]
    available_diagnostic_sources: List[str]

    # Diagnostic Tools & Collected Evidence
    tool_execution_results: List[Dict[str, Any]]
    collected_evidence: List[Dict[str, Any]]

    # Evidence Analysis & Patterns
    evidence_analysis: Dict[str, Any]

    # Root Cause Hypotheses
    hypotheses: List[Dict[str, Any]]

    # Validation Results
    validation_results: Dict[str, Any]

    # Final Formatted Output
    investigation_context: str
    investigation_result: Optional[Dict[str, Any]]

    # Workflow Execution Metadata
    execution_status: str
    errors: List[str]
